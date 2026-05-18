import { describe, expect, it } from "vitest";
import { createServer } from "../../src/server.js";

describe("POST /chat/sessions/:id/messages", () => {
  it("returns 401 without auth", async () => {
    const app = createServer({
      env: {
        CLERK_ISSUER: "https://x.test",
        CLERK_JWKS_URL: "https://x.test/jwks.json",
      },
    });
    const res = await app.request(
      "/chat/sessions/00000000-0000-0000-0000-000000000000/messages",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ content: "hi" }),
      },
    );
    expect(res.status).toBe(401);
  });

  it("returns 400 for a malformed session UUID even with auth (we won't test live; this verifies the route is wired)", async () => {
    // With skipAuth: true the Clerk middleware doesn't run, so the route
    // handler executes directly. But without a real DB connection, anything
    // that hits the DB will throw. The UUID validation happens BEFORE the DB
    // lookup, so this still works.
    const app = createServer({ skipAuth: true });
    const res = await app.request(
      "/chat/sessions/not-a-uuid/messages",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ content: "hi" }),
      },
    );
    expect(res.status).toBe(400);
  });
});
