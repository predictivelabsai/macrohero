# MacroHero — TypeScript Refactor Migration Notes

This document captures the operational state and rollback procedure during
the Python → TypeScript backend cutover. Keep it through and after Phase 6.

## Cutover state machine

| Phase | FE → backend | Python `api` | TS `api-ts` |
|-------|--------------|--------------|-------------|
| Pre-Phase 5 | Python | deployed, public | not deployed |
| Phase 5 Task 4 | Python | deployed, public | deployed, public (smoke-only) |
| Phase 5 Task 7 onward | TS | deployed (rollback target) | deployed, public |
| Phase 6 | TS | retired | deployed, public, renamed `api` |

## Rollback procedure

**Post-Phase 6:** the Python `api` service and source tree are gone. There
is no one-button rollback. If you need to restore the Python api:

1. Find the commit that landed Phase 6 deletion in `git log` and `git revert`
   it. This brings back `docker-compose.yaml`'s `api` block AND the `api/`
   source tree.
2. Push and redeploy. Coolify rebuilds the `api` service.
3. Flip the web service's `NEXT_PUBLIC_API_URL` back to `${SERVICE_URL_API}`
   (or the equivalent hard-coded Python sslip.io URL).

**Pre-Phase 6 (kept for history):** during the Phase 5 soak window the
Python `api` ran alongside the TS service; rollback was a one-commit
revert of the FE flip with the Python container already warm.

## Forward-only artifacts (cannot be rolled back without manual work)

- New rows in `chat_messages` and `chat_sessions` written during the cutover
  window persist regardless of which api is in front. The DB schema is shared.
- The Drizzle schema (`packages/db/src/schema.ts`) treats the existing
  `macrohero_new` Postgres schema as the source of truth via `drizzle-kit pull`.
  No schema changes happen in Phase 5; Alembic remains the migration tool.

## Final Alembic revision

The last Alembic revision applied before retiring Python in Phase 6:

```
c03170a03cb8  (initial_schema)
```

This is the revision Drizzle now assumes the DB matches. Any future schema
change goes through Drizzle (`drizzle-kit generate` + `drizzle-kit migrate`).

## Cutover dates

- Phase 5 parallel deploy: 2026-05-19
- Phase 5 cutover (FE flipped): 2026-05-19
- Phase 5 soak ended (Phase 6 begins): 2026-05-19 (soak compressed; TS api
  verified live with smoke tests + browser-driven end-to-end before Phase 6)
