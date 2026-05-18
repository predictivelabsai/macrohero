import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { describe, expect, it, vi } from "vitest";

// Mock both subagents BEFORE importing the supervisor module.
const fakeResearch = { name: "research", invoke: vi.fn(), stream: vi.fn() };
const fakeAnalytics = { name: "analytics", invoke: vi.fn(), stream: vi.fn() };

vi.mock("../src/subagents/research.js", () => ({
  makeResearchSubagent: () => fakeResearch,
}));
vi.mock("../src/subagents/analytics.js", () => ({
  makeAnalyticsSubagent: () => fakeAnalytics,
}));

// Mock createSupervisor so we can verify the composition without running the
// real graph (the real graph requires a fully functional ChatModel for
// orchestration; that's covered in graph-integration.test.ts).
const compiledStub = { invoke: vi.fn(), streamEvents: vi.fn() };
const createSupervisorMock = vi.fn(() => ({ compile: () => compiledStub }));
vi.mock("@langchain/langgraph-supervisor", () => ({
  createSupervisor: createSupervisorMock,
}));

const { makeSupervisor } = await import("../src/supervisor.js");

describe("makeSupervisor", () => {
  it("composes both subagents with the supervisor prompt and an llm", () => {
    const llmStub = { invoke: vi.fn() } as any;
    const agent = makeSupervisor({ llm: llmStub });

    expect(createSupervisorMock).toHaveBeenCalledWith(
      expect.objectContaining({
        agents: expect.arrayContaining([fakeResearch, fakeAnalytics]),
        llm: llmStub,
        prompt: expect.stringContaining("MacroHero"),
      }),
    );
    expect(agent).toBe(compiledStub);
  });
});
