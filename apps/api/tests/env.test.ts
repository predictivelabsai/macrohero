import { describe, expect, it } from "vitest";
import { parseEnv } from "../src/env.js";

describe("parseEnv", () => {
  it("accepts a complete valid env", () => {
    const env = parseEnv({
      DATABASE_URL: "postgresql://u:p@localhost:5432/db",
      CLERK_ISSUER: "https://x.clerk.dev",
      CLERK_JWKS_URL: "https://x.clerk.dev/.well-known/jwks.json",
      CORS_ORIGINS: "http://localhost:3000",
      PORT: "8002",
    });
    expect(env.DATABASE_URL).toBe("postgresql://u:p@localhost:5432/db");
    expect(env.PORT).toBe(8002);
    expect(env.CORS_ORIGINS).toEqual(["http://localhost:3000"]);
  });

  it("strips +asyncpg driver suffix from DATABASE_URL", () => {
    const env = parseEnv({
      DATABASE_URL: "postgresql+asyncpg://u:p@localhost:5432/db",
      CLERK_ISSUER: "https://x.clerk.dev",
      CLERK_JWKS_URL: "https://x.clerk.dev/.well-known/jwks.json",
      CORS_ORIGINS: "http://localhost:3000",
    });
    expect(env.DATABASE_URL).toBe("postgresql://u:p@localhost:5432/db");
  });

  it("splits CORS_ORIGINS on commas and trims", () => {
    const env = parseEnv({
      DATABASE_URL: "postgresql://u:p@localhost:5432/db",
      CLERK_ISSUER: "https://x.clerk.dev",
      CLERK_JWKS_URL: "https://x.clerk.dev/.well-known/jwks.json",
      CORS_ORIGINS: "http://a.test, http://b.test , http://c.test",
    });
    expect(env.CORS_ORIGINS).toEqual([
      "http://a.test",
      "http://b.test",
      "http://c.test",
    ]);
  });

  it("defaults PORT to 8002 if absent", () => {
    const env = parseEnv({
      DATABASE_URL: "postgresql://u:p@localhost:5432/db",
      CLERK_ISSUER: "https://x.clerk.dev",
      CLERK_JWKS_URL: "https://x.clerk.dev/.well-known/jwks.json",
      CORS_ORIGINS: "http://localhost:3000",
    });
    expect(env.PORT).toBe(8002);
  });

  it("throws on missing DATABASE_URL", () => {
    expect(() =>
      parseEnv({
        CLERK_ISSUER: "https://x.clerk.dev",
        CLERK_JWKS_URL: "https://x.clerk.dev/.well-known/jwks.json",
        CORS_ORIGINS: "http://localhost:3000",
      }),
    ).toThrow(/DATABASE_URL/);
  });
});
