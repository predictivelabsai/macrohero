import { Hono } from "hono";
import { and, asc, desc, eq } from "drizzle-orm";
import type { MiddlewareHandler } from "hono";
import {
  chatMessages,
  chatSessions,
  users,
} from "@macrohero/db";
import { chatActionSchema, chatPartSchema } from "@macrohero/shared";
import { getDb } from "../db.js";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface ChatSessionRoutesOptions {
  auth?: MiddlewareHandler;
}

export function makeChatSessionRoutes(opts: ChatSessionRoutesOptions): Hono {
  const r = new Hono();
  if (opts.auth) r.use("/chat/sessions", opts.auth);
  if (opts.auth) r.use("/chat/sessions/*", opts.auth);

  r.get("/chat/sessions", async (c) => {
    const userId = c.get("userId") as string;
    const db = getDb();
    await ensureUser(userId);

    const rows = await db
      .select()
      .from(chatSessions)
      .where(eq(chatSessions.userId, userId))
      .orderBy(desc(chatSessions.updatedAt))
      .limit(100);
    return c.json(rows.map(toSummary));
  });

  r.post("/chat/sessions", async (c) => {
    const userId = c.get("userId") as string;
    const db = getDb();
    await ensureUser(userId);

    const [row] = await db
      .insert(chatSessions)
      .values({ userId, title: "New chat" })
      .returning();
    if (!row) throw new Error("session insert returned no row");

    return c.json({ ...toSummary(row), messages: [] }, 201);
  });

  r.get("/chat/sessions/:id", async (c) => {
    const userId = c.get("userId") as string;
    const id = c.req.param("id");
    if (!UUID_RE.test(id)) {
      return c.json({ detail: "Invalid session id" }, 400);
    }

    const db = getDb();
    const [session] = await db
      .select()
      .from(chatSessions)
      .where(and(eq(chatSessions.id, id), eq(chatSessions.userId, userId)));
    if (!session) {
      return c.json({ detail: "Chat session not found" }, 404);
    }

    const messages = await db
      .select()
      .from(chatMessages)
      .where(eq(chatMessages.sessionId, id))
      .orderBy(asc(chatMessages.ordinal));

    return c.json({
      ...toSummary(session),
      messages: messages.map((m) => ({
        id: m.id,
        ordinal: m.ordinal,
        role: m.role,
        content: m.content,
        reasoning: m.reasoning,
        actions: chatActionSchema.array().parse(m.actionsJsonb),
        parts: chatPartSchema.array().parse(m.partsJsonb),
        created_at: m.createdAt.toISOString(),
      })),
    });
  });

  r.delete("/chat/sessions/:id", async (c) => {
    const userId = c.get("userId") as string;
    const id = c.req.param("id");
    if (!UUID_RE.test(id)) {
      return c.json({ detail: "Invalid session id" }, 400);
    }

    const db = getDb();
    const result = await db
      .delete(chatSessions)
      .where(and(eq(chatSessions.id, id), eq(chatSessions.userId, userId)))
      .returning({ id: chatSessions.id });

    if (result.length === 0) {
      return c.json({ detail: "Chat session not found" }, 404);
    }
    return c.body(null, 204);
  });

  return r;
}

async function ensureUser(userId: string): Promise<void> {
  const db = getDb();
  await db
    .insert(users)
    .values({ id: userId })
    .onConflictDoNothing({ target: users.id });
}

function toSummary(row: typeof chatSessions.$inferSelect) {
  return {
    id: row.id,
    title: row.title,
    created_at: row.createdAt.toISOString(),
    updated_at: row.updatedAt.toISOString(),
  };
}
