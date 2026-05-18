import { z } from "zod";

const rawEnvSchema = z.object({
  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),
  CLERK_ISSUER: z.string().url("CLERK_ISSUER must be a URL"),
  CLERK_JWKS_URL: z.string().url("CLERK_JWKS_URL must be a URL"),
  CORS_ORIGINS: z.string().min(1, "CORS_ORIGINS is required"),
  PORT: z.string().regex(/^\d+$/, "PORT must be a number").optional(),
});

function normalizeDatabaseUrl(url: string): string {
  // SQLAlchemy uses `postgresql+asyncpg://` to select the async driver. postgres.js
  // doesn't know that scheme; strip the suffix.
  if (url.startsWith("postgresql+asyncpg://")) {
    return "postgresql://" + url.slice("postgresql+asyncpg://".length);
  }
  if (url.startsWith("postgres://")) {
    return "postgresql://" + url.slice("postgres://".length);
  }
  return url;
}

export interface AppEnv {
  DATABASE_URL: string;
  CLERK_ISSUER: string;
  CLERK_JWKS_URL: string;
  CORS_ORIGINS: string[];
  PORT: number;
}

export function parseEnv(raw: Record<string, string | undefined>): AppEnv {
  const parsed = rawEnvSchema.parse(raw);
  return {
    DATABASE_URL: normalizeDatabaseUrl(parsed.DATABASE_URL),
    CLERK_ISSUER: parsed.CLERK_ISSUER,
    CLERK_JWKS_URL: parsed.CLERK_JWKS_URL,
    CORS_ORIGINS: parsed.CORS_ORIGINS.split(",")
      .map((o) => o.trim())
      .filter((o) => o.length > 0),
    PORT: parsed.PORT ? Number(parsed.PORT) : 8002,
  };
}

// Lazy module-level singleton used by routes/middleware. Tests use `parseEnv` directly.
let cached: AppEnv | undefined;
export function getEnv(): AppEnv {
  if (!cached) {
    cached = parseEnv(process.env);
  }
  return cached;
}
