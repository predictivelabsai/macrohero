import { tool } from "@langchain/core/tools";
import { tavily } from "@tavily/core";
import { z } from "zod";

const DESCRIPTION = `Search the web for current events, recent news, or named entities
the model doesn't have detailed knowledge of.

Use this BEFORE running a factor projection whenever the user references a
specific recent event, ongoing crisis, person, place, or named scenario you
can't confidently identify on your own (examples: "Hormuz war", "latest CPI
print", "yesterday's ECB decision"). Returns search snippets to ground
downstream reasoning. Search results are qualitative — never quote numbers
from them in user-facing output.

Returns: {query, answer, results: [{title, url, content}], error}.`;

const argsSchema = z.object({
  query: z.string().min(3).max(200).describe(
    "Search query. Be specific: include the event name and any timeframe.",
  ),
  max_results: z.number().int().min(1).max(10).default(5).describe(
    "Number of search snippets to return.",
  ),
});

interface SearchResult {
  query: string;
  answer: string | null;
  results: Array<{ title: string; url: string; content: string }>;
  error: string | null;
}

// Lazy-instantiated client. Allows env var to be set after module import.
let cachedClient: ReturnType<typeof tavily> | undefined;
function getClient(): ReturnType<typeof tavily> {
  if (!cachedClient) {
    cachedClient = tavily({ apiKey: process.env.TAVILY_API_KEY ?? "" });
  }
  return cachedClient;
}

export const searchCurrentEvents = tool(
  async ({ query, max_results }): Promise<SearchResult> => {
    try {
      const data = (await getClient().search(query, {
        maxResults: max_results,
        includeAnswer: true,
      })) as {
        answer?: string | null;
        results?: Array<{ title?: string; url?: string; content?: string }>;
      };
      return {
        query,
        answer: data.answer ?? null,
        results: (data.results ?? []).map((r) => ({
          title: r.title ?? "",
          url: r.url ?? "",
          content: (r.content ?? "").slice(0, 600),
        })),
        error: null,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        query,
        answer: null,
        results: [],
        error: `Search failed: ${message}`.slice(0, 200),
      };
    }
  },
  {
    name: "search_current_events",
    description: DESCRIPTION,
    schema: argsSchema,
  },
);
