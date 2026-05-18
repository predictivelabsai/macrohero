# Multi-stage build for a pnpm-monorepo workspace member (apps/web).
# Build context MUST be the monorepo root (see docker-compose.yaml).

FROM node:22-alpine AS deps

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

# Copy only the manifests + lockfile so dep install is cached when source changes.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/

RUN pnpm install --frozen-lockfile --filter web...

FROM node:22-alpine AS builder

ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_CLERK_SIGN_IN_URL
ARG NEXT_PUBLIC_CLERK_SIGN_UP_URL
ARG NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL
ARG NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL
ARG NEXT_PUBLIC_API_URL

ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY} \
    NEXT_PUBLIC_CLERK_SIGN_IN_URL=${NEXT_PUBLIC_CLERK_SIGN_IN_URL} \
    NEXT_PUBLIC_CLERK_SIGN_UP_URL=${NEXT_PUBLIC_CLERK_SIGN_UP_URL} \
    NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=${NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL} \
    NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL=${NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL} \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate

# Bring forward the hoisted node_modules and full workspace.
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web ./apps/web

WORKDIR /repo/apps/web
RUN pnpm build

FROM node:22-alpine AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

# Preserve the builder's /repo layout so pnpm's relative symlinks in
# apps/web/node_modules can resolve into /repo/node_modules at runtime.
WORKDIR /repo/apps/web

COPY --from=builder /repo/node_modules /repo/node_modules
COPY --from=builder /repo/apps/web/node_modules ./node_modules
COPY --from=builder /repo/apps/web/package.json ./package.json
COPY --from=builder /repo/apps/web/public ./public
COPY --from=builder /repo/apps/web/.next ./.next

EXPOSE 3000

CMD ["./node_modules/.bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
