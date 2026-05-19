import { Hono } from "hono";
import type { MiddlewareHandler } from "hono";
import { eq } from "drizzle-orm";
import { z } from "zod";
import { chatMessages, chatSessions, users } from "@macrohero/db";
import { summarizeTitle } from "@macrohero/agent";
import { getDb } from "../db.js";
import { streamTurn } from "../chat/stream-turn.js";

const sendMessageSchema = z.object({
  content: z.string().min(1).max(8000),
});

const TITLE_HARD_CAP = 200;

function initialTitle(content: string): string {
  const cleaned = content.split(/\s+/).filter(Boolean).join(" ");
  if (!cleaned) return "New chat";
  return cleaned.slice(0, TITLE_HARD_CAP).trimEnd();
}

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

export interface ChatStartRoutesOptions {
  auth?: MiddlewareHandler;
}

export function makeChatStartRoutes(opts: ChatStartRoutesOptions): Hono {
  const r = new Hono();
  if (opts.auth) r.use("/chat/start", opts.auth);

  r.post("/chat/start", async (c) => {
    const userId = (c.get("userId") as string | undefined) ?? "test-user";

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

    // Ensure user row exists (lazy upsert, same as /me).
    await db.insert(users).values({ id: userId }).onConflictDoNothing({ target: users.id });

    const title = initialTitle(parsed.data.content);
    const [session] = await db
      .insert(chatSessions)
      .values({ userId, title })
      .returning();
    if (!session) {
      return c.json({ detail: "Failed to create chat session" }, 500);
    }

    await db.insert(chatMessages).values({
      sessionId: session.id,
      ordinal: 0,
      role: "user",
      content: parsed.data.content,
      actionsJsonb: [],
    });

    const titleTask = spawnTitleTask(session.id, parsed.data.content);

    return streamTurn({
      sessionId: session.id,
      history: [{ role: "user", content: parsed.data.content }],
      assistantOrdinal: 1,
      titleTask,
      prelude: [
        {
          type: "data-session",
          id: `sess_${session.id}`,
          data: { sessionId: session.id, title },
          transient: true,
        },
      ],
    });
  });

  return r;
}
