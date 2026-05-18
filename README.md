# MacroHero

MacroHero is a Clerk-authenticated web app with a FastAPI backend, Postgres persistence, and a streaming LLM chat interface.

## Layout

```text
apps/
  web/    Next.js + Tailwind + Clerk (TypeScript)
packages/ Shared TS packages (none yet; populated in later refactor phases)
api/      FastAPI + SQLAlchemy 2.0 + Alembic (Python 3.12)
```

pnpm workspaces; lockfile at root. The Python `api/` is not yet part of the workspace.

## Prerequisites

- Node 20+ and pnpm 10+
- `uv` for the Python backend
- A Postgres database, provided through `DATABASE_URL`
- Clerk account and JWT settings
- DeepSeek API key for the chat assistant

## Run Locally

API (from repo root):

```bash
cd api
uv sync
uv run alembic upgrade head
uv run uvicorn macrohero.main:app --reload --port 8000
```

Web (from repo root):

```bash
pnpm install
pnpm dev:web
```

Or directly:

```bash
cd apps/web
pnpm dev
```

Frontend runs on http://localhost:3000. The API runs on http://localhost:8000.

## Environment

Copy `.env.example` to `apps/web/.env.local` and `api/.env`, then fill in the values for Clerk, Postgres, CORS, and DeepSeek.
