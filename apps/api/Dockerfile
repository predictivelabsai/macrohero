# Multi-stage build for a pnpm-monorepo workspace member (apps/api).
# Build context MUST be the monorepo root (see docker-compose.yaml when added in Phase 4).

FROM node:22-alpine AS deps

ENV NODE_ENV=production

WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/api/package.json ./apps/api/
COPY packages/agent/package.json ./packages/agent/
COPY packages/db/package.json ./packages/db/
COPY packages/shared/package.json ./packages/shared/
COPY packages/tools/package.json ./packages/tools/

RUN pnpm install --frozen-lockfile --filter @macrohero/api...

FROM node:22-alpine AS runner

ENV NODE_ENV=production \
    PORT=8002

WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/api/node_modules ./apps/api/node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/api ./apps/api
COPY packages/agent ./packages/agent
COPY packages/db ./packages/db
COPY packages/shared ./packages/shared
COPY packages/tools ./packages/tools

WORKDIR /repo/apps/api
EXPOSE 8002

# Use tsx (now a runtime dep) instead of node --experimental-strip-types.
# tsx handles both type stripping AND the TypeScript-ESM convention where
# `import "./db.js"` resolves to `./db.ts` — Node's bare --strip-types flag
# doesn't rewrite the import path, so it fails with ERR_MODULE_NOT_FOUND.
CMD ["pnpm", "exec", "tsx", "src/index.ts"]
