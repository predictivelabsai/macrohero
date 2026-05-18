import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock @tavily/core BEFORE importing the tool.
const mockSearch = vi.fn();
vi.mock("@tavily/core", () => ({
  tavily: vi.fn(() => ({ search: mockSearch })),
}));

const { searchCurrentEvents } = await import(
  "../../src/research/search-current-events.js"
);

describe("searchCurrentEvents tool", () => {
  beforeEach(() => {
    mockSearch.mockReset();
  });

  it("calls tavily.search with the right args", async () => {
    mockSearch.mockResolvedValue({
      query: "hormuz war",
      answer: "summary",
      results: [],
    });

    await searchCurrentEvents.invoke({ query: "hormuz war", max_results: 3 });

    expect(mockSearch).toHaveBeenCalledWith("hormuz war", {
      maxResults: 3,
      includeAnswer: true,
    });
  });

  it("returns the parsed result with content truncated to 600 chars", async () => {
    const longContent = "x".repeat(900);
    mockSearch.mockResolvedValue({
      query: "test",
      answer: "answer text",
      results: [
        {
          title: "Article",
          url: "https://example.test/a",
          content: longContent,
        },
      ],
    });

    const result = await searchCurrentEvents.invoke({ query: "test" });

    expect(result).toMatchObject({
      query: "test",
      answer: "answer text",
      error: null,
    });
    expect(result.results).toHaveLength(1);
    expect(result.results[0]!.content.length).toBe(600);
    expect(result.results[0]!.content).toBe("x".repeat(600));
  });

  it("defaults max_results to 5", async () => {
    mockSearch.mockResolvedValue({ query: "x", results: [] });

    await searchCurrentEvents.invoke({ query: "anything" });

    expect(mockSearch).toHaveBeenCalledWith("anything", {
      maxResults: 5,
      includeAnswer: true,
    });
  });

  it("returns a structured error envelope when tavily throws", async () => {
    mockSearch.mockRejectedValue(new Error("Tavily HTTP 429"));

    const result = await searchCurrentEvents.invoke({ query: "fail case" });

    expect(result).toMatchObject({
      query: "fail case",
      answer: null,
      results: [],
    });
    expect(result.error).toContain("429");
  });
});
