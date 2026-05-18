import { createDb, type Database } from "@macrohero/db";
import { getEnv } from "./env.js";

interface DbHandle {
  db: Database;
  sql: ReturnType<typeof createDb>["sql"];
}

let cached: DbHandle | undefined;

export function getDb(): Database {
  if (!cached) {
    const env = getEnv();
    cached = createDb({ url: env.DATABASE_URL, poolMax: 10, statementTimeoutMs: 30_000 });
  }
  return cached.db;
}

export async function closeDb(): Promise<void> {
  if (cached) {
    await cached.sql.end({ timeout: 5 });
    cached = undefined;
  }
}

// Test-only override. Lets the Testcontainers helper inject a Database bound to the
// test container rather than the env-derived production URL.
export function _setDbForTesting(handle: DbHandle | undefined): void {
  cached = handle;
}
