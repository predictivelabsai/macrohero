import { Hono } from "hono";
import { cors } from "hono/cors";
import { getEnv } from "./env.js";
import { clerkAuth } from "./middleware/clerk.js";
import { healthRoutes } from "./routes/health.js";
import { makeMeRoutes } from "./routes/me.js";
import { makeChatSessionRoutes } from "./routes/chat-sessions.js";
import { makeChatMessagesRoutes } from "./routes/chat-messages.js";
import { makeChatStartRoutes } from "./routes/chat-start.js";

export interface CreateServerOptions {
  /** Test-only: bypass auth + override env vars from a partial. */
  skipAuth?: boolean;
  env?: { CLERK_ISSUER: string; CLERK_JWKS_URL: string; CORS_ORIGINS?: string[] };
}

export function createServer(opts: CreateServerOptions = {}): Hono {
  const app = new Hono();

  const resolved =
    opts.env ??
    (opts.skipAuth
      ? undefined
      : {
          CLERK_ISSUER: getEnv().CLERK_ISSUER,
          CLERK_JWKS_URL: getEnv().CLERK_JWKS_URL,
          CORS_ORIGINS: getEnv().CORS_ORIGINS,
        });

  app.use(
    "*",
    cors({
      origin: (origin) => {
        if (!resolved?.CORS_ORIGINS || resolved.CORS_ORIGINS.length === 0) return origin ?? "*";
        return resolved.CORS_ORIGINS.includes(origin ?? "") ? origin : "";
      },
      credentials: true,
    }),
  );

  // /healthz is always public.
  app.route("/", healthRoutes);

  // Protected routes.
  const auth = opts.skipAuth
    ? undefined
    : clerkAuth({
        jwksUrl: resolved!.CLERK_JWKS_URL,
        issuer: resolved!.CLERK_ISSUER,
      });

  app.route("/", makeMeRoutes({ auth }));
  app.route("/", makeChatSessionRoutes({ auth }));
  app.route("/", makeChatMessagesRoutes({ auth }));
  app.route("/", makeChatStartRoutes({ auth }));

  return app;
}
