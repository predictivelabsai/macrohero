import { Hono } from "hono";
import type { MiddlewareHandler } from "hono";
import { and, eq } from "drizzle-orm";
import { z } from "zod";
import { chatMessages, chatSessions, users } from "@macrohero/db";
import { summarizeTitle } from "@macrohero/agent";
import { getDb } from "../db.js";
import { streamTurn, loadHistory, nextOrdinal } from "../chat/stream-turn.js";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const sendMessageSchema = z.object({
  content: z.string().min(1).max(8000),
});

const TITLE_HARD_CAP = 200;

function initialTitle(content: string): string {
  const cleaned = content.split(/\s+/).filter(Boolean).join(" ");
  if (!cleaned) return "New chat";
  return cleaned.slice(0, TITLE_HARD_CAP).trimEnd();
}

/**
 * Fire a background title refresh against chat_sessions.title. The promise
 * resolves to the new title on success or null on any failure. The promise
 * itself never rejects.
 */
function spawnTitleTask(sessionId: string, content: string): Promise<string | null> {
  return summarizeTitle(content)
    .then(async (title) => {
      if (!title) return null;
      try {
        await getDb()
          .update(chatSessions)
          .set({ title })
          .where(eq(chatSessions.id, sessionId));
        return title;
      } catch (err) {
        console.warn("[spawnTitleTask] DB update failed:", err);
        return null;
      }
    })
    .catch((err) => {
      console.warn("[spawnTitleTask] summarizeTitle threw:", err);
      return null;
    });
}

export interface ChatMessagesRoutesOptions {
  auth?: MiddlewareHandler;
}

export function makeChatMessagesRoutes(opts: ChatMessagesRoutesOptions): Hono {
  const r = new Hono();
  if (opts.auth) r.use("/chat/sessions/:id/messages", opts.auth);

  r.post("/chat/sessions/:id/messages", async (c) => {
    const userId = (c.get("userId") as string | undefined) ?? "test-user";
    const id = c.req.param("id");
    if (!UUID_RE.test(id)) {
      return c.json({ detail: "Invalid session id" }, 400);
    }

    let body: unknown;
    try {
      body = await c.req.json();
    } catch {
      return c.json({ detail: "Invalid JSON body" }, 400);
    }
    const parsed = sendMessageSchema.safeParse(body);
    if (!parsed.success) {
      return c.json({ detail: parsed.error.issues[0]?.message ?? "Invalid body" }, 400);
    }

    const db = getDb();

    // Ownership check.
    const [session] = await db
      .select()
      .from(chatSessions)
      .where(and(eq(chatSessions.id, id), eq(chatSessions.userId, userId)));
    if (!session) {
      return c.json({ detail: "Chat session not found" }, 404);
    }

    // Compute the next ordinal and insert the user's message.
    const userOrdinal = await nextOrdinal(id);
    await db.insert(chatMessages).values({
      sessionId: id,
      ordinal: userOrdinal,
      role: "user",
      content: parsed.data.content,
      actionsJsonb: [],
    });

    // First user message becomes the session title. Write a synchronous
    // placeholder, then spawn the LLM summarizer in the background.
    const isFirstUserMessage = userOrdinal === 0;
    let titleTask: Promise<string | null> | undefined;
    if (isFirstUserMessage) {
      await db
        .update(chatSessions)
        .set({ title: initialTitle(parsed.data.content) })
        .where(eq(chatSessions.id, id));
      titleTask = spawnTitleTask(id, parsed.data.content);
    }

    const history = await loadHistory(id);
    return streamTurn({
      sessionId: id,
      history,
      assistantOrdinal: userOrdinal + 1,
      titleTask,
    });
  });

  return r;
}
