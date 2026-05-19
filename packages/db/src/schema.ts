import { randomUUID } from "node:crypto";
import { sql } from "drizzle-orm";
import {
  index,
  integer,
  jsonb,
  pgSchema,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import type { ChatAction, ChatPart } from "@macrohero/shared";

export const macrohero = pgSchema("macrohero_new");

export const users = macrohero.table("users", {
  id: text("id").primaryKey(),
  email: text("email"),
  // Python: String(100). Postgres TEXT is effectively unbounded; length cap is enforced
  // at the API boundary via the Zod schema in @macrohero/shared.
  displayName: text("display_name"),
  // Python: String(64). Same approach — length capped via Zod.
  timezone: text("timezone"),
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .default(sql`now()`),
  updatedAt: timestamp("updated_at", { withTimezone: true })
    .notNull()
    .default(sql`now()`)
    .$onUpdate(() => new Date()),
});

export const chatSessions = macrohero.table(
  "chat_sessions",
  {
    // The existing Postgres `chat_sessions.id` column was created by Alembic
    // without a SQL-level default (the original SQLAlchemy model uses a Python
    // default `uuid.uuid4` that runs in the ORM). Drizzle's `defaultRandom()`
    // generates a SQL `DEFAULT gen_random_uuid()` clause, which the existing
    // column doesn't have — INSERTs without explicit id would send NULL.
    // `$defaultFn` runs in TS at insert time, matching the SQLAlchemy behavior.
    id: uuid("id").primaryKey().$defaultFn(() => randomUUID()),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    title: text("title").notNull().default("New chat"),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .default(sql`now()`),
    updatedAt: timestamp("updated_at", { withTimezone: true })
      .notNull()
      .default(sql`now()`)
      .$onUpdate(() => new Date()),
  },
  (t) => ({
    userIdx: index("ix_chat_sessions_user_id").on(t.userId),
    updatedIdx: index("ix_chat_sessions_updated_at").on(t.updatedAt),
  }),
);

export const chatMessages = macrohero.table(
  "chat_messages",
  {
    // Same as chat_sessions.id — the column has no SQL-level default; generate
    // the UUID in TS at insert time.
    id: uuid("id").primaryKey().$defaultFn(() => randomUUID()),
    sessionId: uuid("session_id")
      .notNull()
      .references(() => chatSessions.id, { onDelete: "cascade" }),
    ordinal: integer("ordinal").notNull(),
    // "user" | "assistant" — length cap (20) enforced at API boundary.
    role: text("role").notNull(),
    content: text("content").notNull().default(""),
    reasoning: text("reasoning").notNull().default(""),
    actionsJsonb: jsonb("actions_jsonb").$type<ChatAction[]>().notNull().default([]),
    partsJsonb: jsonb("parts_jsonb").$type<ChatPart[]>().notNull().default([]),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .default(sql`now()`),
  },
  (t) => ({
    sessionOrdinalUq: uniqueIndex("uq_chat_messages_session_ordinal").on(
      t.sessionId,
      t.ordinal,
    ),
    sessionIdx: index("ix_chat_messages_session_id").on(t.sessionId),
  }),
);
