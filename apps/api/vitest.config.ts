import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Prefer the "browser" export condition so packages that ship a Web-API
    // build (notably `jose`) load the fetch-based JWKS fetcher instead of the
    // Node ESM build that calls `node:https.get` directly. Tests can then
    // intercept JWKS retrieval by patching `global.fetch`.
    conditions: ["browser", "import", "default"],
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
    server: {
      deps: {
        // Inline LangChain + OpenTelemetry-ecosystem deps so Vite processes
        // them and rewrites their extension-less ESM imports (e.g. OTel's
        // `./baggage/utils` -> `./baggage/utils.js`). Without this, Node's
        // strict ESM resolver fails on any test that touches @macrohero/agent.
        inline: [
          /@opentelemetry\//,
          /@langchain\//,
          /@macrohero\/agent/,
          /langgraph/,
        ],
      },
    },
  },
});
