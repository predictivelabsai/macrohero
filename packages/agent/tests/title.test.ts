import { AIMessage } from "@langchain/core/messages";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Stub makeFlashLLM before importing the title module.
const stubInvoke = vi.fn();
vi.mock("../src/llm.js", () => ({
  makeFlashLLM: () => ({ invoke: stubInvoke }),
}));

const { summarizeTitle } = await import("../src/title.js");

describe("summarizeTitle", () => {
  beforeEach(() => {
    stubInvoke.mockReset();
  });

  it("returns the LLM's response trimmed and cleaned", async () => {
    stubInvoke.mockResolvedValue(new AIMessage('  "Oil shock effect on EUR/USD"  '));
    const title = await summarizeTitle("What if oil falls 10%?");
    expect(title).toBe("Oil shock effect on EUR/USD");
  });

  it("strips trailing punctuation", async () => {
    stubInvoke.mockResolvedValue(new AIMessage("Macro tail risks for 2026."));
    const title = await summarizeTitle("Macro tail risks?");
    expect(title).toBe("Macro tail risks for 2026");
  });

  it("caps to 200 chars", async () => {
    stubInvoke.mockResolvedValue(new AIMessage("a".repeat(500)));
    const title = await summarizeTitle("anything");
    expect(title!.length).toBe(200);
  });

  it("takes only the first line if the model emits a multi-line response", async () => {
    stubInvoke.mockResolvedValue(new AIMessage("First line title\nExtra stuff"));
    const title = await summarizeTitle("anything");
    expect(title).toBe("First line title");
  });

  it("returns null on empty input", async () => {
    const title = await summarizeTitle("   ");
    expect(title).toBeNull();
  });

  it("returns null on LLM error", async () => {
    stubInvoke.mockRejectedValue(new Error("rate limited"));
    const title = await summarizeTitle("hello");
    expect(title).toBeNull();
  });

  it("returns null on empty LLM output", async () => {
    stubInvoke.mockResolvedValue(new AIMessage(""));
    const title = await summarizeTitle("hello");
    expect(title).toBeNull();
  });
});
