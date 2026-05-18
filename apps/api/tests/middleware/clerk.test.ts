import { Hono } from "hono";
import { beforeAll, describe, expect, it } from "vitest";
import { clerkAuth } from "../../src/middleware/clerk.js";
import { setupTestJwt, type TestJwtSetup } from "../helpers/test-jwt.js";

describe("clerkAuth middleware", () => {
  let jwt: TestJwtSetup;
  let app: Hono;

  beforeAll(async () => {
    jwt = await setupTestJwt();

    // The middleware fetches JWKS from a URL. Use Hono itself to serve our test JWKS.
    const jwksApp = new Hono();
    jwksApp.get("/jwks.json", (c) => c.json(jwt.jwks));

    // Patch global fetch so the middleware's createRemoteJWKSet resolves locally.
    const originalFetch = global.fetch;
    global.fetch = (async (url: string | URL, init?: RequestInit) => {
      const u = typeof url === "string" ? url : url.toString();
      if (u === "https://test.clerk.test/.well-known/jwks.json") {
        return jwksApp.fetch(new Request("http://_/jwks.json"));
      }
      return originalFetch(url, init);
    }) as typeof fetch;

    app = new Hono();
    app.use(
      "*",
      clerkAuth({
        jwksUrl: "https://test.clerk.test/.well-known/jwks.json",
        issuer: jwt.issuer,
      }),
    );
    app.get("/protected", (c) => c.json({ userId: c.get("userId") }));
  });

  it("rejects requests without an Authorization header", async () => {
    const res = await app.request("/protected");
    expect(res.status).toBe(401);
  });

  it("rejects requests with a malformed Authorization header", async () => {
    const res = await app.request("/protected", {
      headers: { authorization: "NotBearer xyz" },
    });
    expect(res.status).toBe(401);
  });

  it("rejects requests with an invalid token", async () => {
    const res = await app.request("/protected", {
      headers: { authorization: "Bearer not-a-jwt" },
    });
    expect(res.status).toBe(401);
  });

  it("rejects tokens with the wrong issuer", async () => {
    const token = await jwt.mintToken({ sub: "user_abc", issuer: "https://wrong.test" });
    const res = await app.request("/protected", {
      headers: { authorization: `Bearer ${token}` },
    });
    expect(res.status).toBe(401);
  });

  it("accepts a valid token and sets userId on the context", async () => {
    const token = await jwt.mintToken({ sub: "user_abc" });
    const res = await app.request("/protected", {
      headers: { authorization: `Bearer ${token}` },
    });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ userId: "user_abc" });
  });

  it("rejects expired tokens", async () => {
    const token = await jwt.mintToken({ sub: "user_abc", ttlSeconds: -10 });
    const res = await app.request("/protected", {
      headers: { authorization: `Bearer ${token}` },
    });
    expect(res.status).toBe(401);
  });
});
