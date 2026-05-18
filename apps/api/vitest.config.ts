import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Prefer the "browser" export condition so packages that ship a Web-API
    // build (notably `jose`) load the fetch-based JWKS fetcher instead of the
    // Node ESM build that calls `node:https.get` directly. Tests can then
    // intercept JWKS retrieval by patching `global.fetch`.
    conditions: ["browser", "import", "module", "default"],
  },
  test: {
    globals: true,
    environment: "node",
    setupFiles: [],
    testTimeout: 30_000,
    hookTimeout: 60_000,
    pool: "forks",
    poolOptions: {
      forks: {
        singleFork: true, // Reuse the same Testcontainers Postgres across tests.
      },
    },
  },
});
