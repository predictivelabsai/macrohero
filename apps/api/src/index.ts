import { serve } from "@hono/node-server";
import { closeDb } from "./db.js";
import { getEnv } from "./env.js";
import { createServer } from "./server.js";

const env = getEnv();
const app = createServer();

const server = serve(
  {
    fetch: app.fetch,
    port: env.PORT,
  },
  (info) => {
    console.log(`api listening on http://localhost:${info.port}`);
  },
);

async function shutdown(signal: NodeJS.Signals): Promise<void> {
  console.log(`received ${signal}, shutting down`);
  server.close();
  await closeDb();
  process.exit(0);
}

process.on("SIGTERM", () => void shutdown("SIGTERM"));
process.on("SIGINT", () => void shutdown("SIGINT"));
