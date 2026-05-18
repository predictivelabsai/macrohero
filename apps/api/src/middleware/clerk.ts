import { createRemoteJWKSet, jwtVerify, errors as joseErrors } from "jose";
import { createMiddleware } from "hono/factory";

export interface ClerkAuthOptions {
  jwksUrl: string;
  issuer: string;
}

// Module-level cache of JWKS sets keyed by URL. The JWKS object handles its own
// remote refresh; we cache the *resolver* so we don't re-fetch on every request.
const jwksCache = new Map<string, ReturnType<typeof createRemoteJWKSet>>();

function getJwks(url: string): ReturnType<typeof createRemoteJWKSet> {
  let jwks = jwksCache.get(url);
  if (!jwks) {
    jwks = createRemoteJWKSet(new URL(url));
    jwksCache.set(url, jwks);
  }
  return jwks;
}

declare module "hono" {
  interface ContextVariableMap {
    userId: string;
  }
}

export function clerkAuth(opts: ClerkAuthOptions) {
  const jwks = getJwks(opts.jwksUrl);

  return createMiddleware(async (c, next) => {
    const authHeader = c.req.header("authorization");
    if (!authHeader || !authHeader.toLowerCase().startsWith("bearer ")) {
      return c.json({ detail: "Missing bearer token" }, 401);
    }
    const token = authHeader.slice("bearer ".length).trim();
    if (!token) {
      return c.json({ detail: "Missing bearer token" }, 401);
    }

    try {
      const { payload } = await jwtVerify(token, jwks, {
        issuer: opts.issuer,
      });
      const sub = payload.sub;
      if (typeof sub !== "string" || !sub) {
        return c.json({ detail: "Token is missing sub claim" }, 401);
      }
      c.set("userId", sub);
      await next();
    } catch (err) {
      const detail =
        err instanceof joseErrors.JOSEError
          ? `Invalid token: ${err.message}`
          : "Invalid token";
      return c.json({ detail }, 401);
    }
  });
}

// Test-only helper to clear the JWKS cache between test files.
export function _resetJwksCacheForTesting(): void {
  jwksCache.clear();
}
