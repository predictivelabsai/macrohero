import { Hono } from "hono";
import { eq } from "drizzle-orm";
import type { MiddlewareHandler } from "hono";
import { users } from "@macrohero/db";
import { meResponseSchema, meUpdateSchema, type MeResponse } from "@macrohero/shared";
import { getDb } from "../db.js";

export interface MeRoutesOptions {
  auth?: MiddlewareHandler;
}

export function makeMeRoutes(opts: MeRoutesOptions): Hono {
  const r = new Hono();
  if (opts.auth) r.use("/me", opts.auth);
  if (opts.auth) r.use("/me/*", opts.auth);

  r.get("/me", async (c) => {
    const userId = c.get("userId") as string;
    const me = await ensureUser(userId);
    return c.json(meResponseSchema.parse(me));
  });

  r.patch("/me", async (c) => {
    const userId = c.get("userId") as string;
    let body: unknown;
    try {
      body = await c.req.json();
    } catch {
      return c.json({ detail: "Invalid JSON body" }, 400);
    }
    const parsed = meUpdateSchema.safeParse(body);
    if (!parsed.success) {
      return c.json({ detail: parsed.error.issues[0]?.message ?? "Invalid body" }, 400);
    }

    await ensureUser(userId);

    const updates: Partial<{ displayName: string | null; timezone: string }> = {};
    if (parsed.data.display_name !== undefined) {
      // Empty string -> null.
      const val = parsed.data.display_name;
      updates.displayName =
        typeof val === "string" && val.trim().length > 0 ? val.trim() : null;
    }
    if (parsed.data.timezone) {
      updates.timezone = parsed.data.timezone;
    }

    const db = getDb();
    if (Object.keys(updates).length > 0) {
      await db.update(users).set(updates).where(eq(users.id, userId));
    }
    const me = await fetchUser(userId);
    return c.json(meResponseSchema.parse(me));
  });

  return r;
}

async function ensureUser(userId: string): Promise<MeResponse> {
  const db = getDb();
  await db
    .insert(users)
    .values({ id: userId })
    .onConflictDoNothing({ target: users.id });
  return fetchUser(userId);
}

async function fetchUser(userId: string): Promise<MeResponse> {
  const db = getDb();
  const [row] = await db.select().from(users).where(eq(users.id, userId));
  if (!row) {
    throw new Error(`User ${userId} not found after ensureUser`);
  }
  return {
    user_id: row.id,
    display_name: row.displayName,
    timezone: row.timezone,
  };
}
