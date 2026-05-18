# Multi-stage build for a pnpm-monorepo workspace member (apps/api).
# Build context MUST be the monorepo root (see docker-compose.yaml when added in Phase 4).

FROM node:22-alpine AS deps

ENV NODE_ENV=production

WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/api/package.json ./apps/api/
COPY packages/db/package.json ./packages/db/
COPY packages/shared/package.json ./packages/shared/

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
COPY packages/db ./packages/db
COPY packages/shared ./packages/shared

WORKDIR /repo/apps/api
EXPOSE 8002

# Node 22+ ships --experimental-strip-types which lets us run .ts files directly
# at runtime without a compile step. Matches the dev workflow (tsx) and avoids
# a tsup/tsc build stage.
CMD ["node", "--experimental-strip-types", "src/index.ts"]
