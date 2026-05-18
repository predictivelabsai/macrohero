import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema.js";

export interface DbOptions {
  url: string;
  poolMax?: number;
  statementTimeoutMs?: number;
}

export function createDb(opts: DbOptions) {
  const sql = postgres(opts.url, {
    max: opts.poolMax ?? 10,
    // Statement-level timeout — matches the 30s soft cap the streaming endpoints will want.
    connection: {
      statement_timeout: opts.statementTimeoutMs ?? 30_000,
    },
  });

  return {
    db: drizzle(sql, { schema }),
    // Expose the raw postgres-js client for graceful shutdown.
    sql,
  };
}

export type Database = ReturnType<typeof createDb>["db"];
