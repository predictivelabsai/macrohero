# MacroHero

MacroHero is a Clerk-authenticated web app for FX scenario analysis. The
chat assistant uses a LangGraph supervisor that delegates between a research
agent (current events) and an analytics agent (factor-projection scenarios),
streaming the multi-agent flow live into the browser.

## Layout

```text
apps/
  web/        Next.js + Tailwind + Clerk (TypeScript)
  api/        Hono + Drizzle + LangGraph (TypeScript, Node 22)
  numerics/   FastAPI projection service (Python 3.12, kept for the numerics)
packages/     Shared TS workspace packages (agent, tools, db, shared)
```

pnpm workspaces; lockfile at root. `apps/numerics` is a Python service that
lives alongside the workspace.

## Prerequisites

- Node 22+ and pnpm 10+
- `uv` for the numerics service
- A Postgres database, provided through `DATABASE_URL`
- Clerk account and JWT settings
- DeepSeek API key for the chat assistant
- Massive (Polygon) API key for factor data
- Tavily API key for web research

## Run Locally

Numerics (from repo root):

```bash
cd apps/numerics
uv sync
uv run uvicorn numerics.main:app --reload --port 8001
```

TS API (from repo root, in another terminal):

```bash
pnpm --filter @macrohero/api dev
```

Web (from repo root, in another terminal):

```bash
pnpm dev:web
```

Frontend runs on http://localhost:3000, the TS api on http://localhost:8002,
numerics on http://localhost:8001. Set `NEXT_PUBLIC_API_URL=http://localhost:8002`
in `apps/web/.env.local` for the FE to reach the local api.

## Environment

Copy the `.env.example` files into the corresponding `.env`/`.env.local`
locations and fill in the values for Clerk, Postgres, CORS, DeepSeek,
Massive, and Tavily.
