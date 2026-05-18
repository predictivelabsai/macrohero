import { describe, expect, it } from "vitest";
import { createServer } from "../../src/server.js";

describe("GET /healthz", () => {
  it("returns 200 with status ok", async () => {
    // /healthz doesn't touch the DB or require auth.
    const app = createServer({ skipAuth: true });
    const res = await app.request("/healthz");
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});
