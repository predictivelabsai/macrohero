-- Adds the per-user "show thinking" display preference (defaults to true so
-- existing users keep the original chat behaviour). Idempotent so it is safe to
-- re-run against an environment where `pnpm --filter @macrohero/db push` has
-- already applied the column.
ALTER TABLE "macrohero_new"."users"
  ADD COLUMN IF NOT EXISTS "show_thinking" boolean NOT NULL DEFAULT true;
