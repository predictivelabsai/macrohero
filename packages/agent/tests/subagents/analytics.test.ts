import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockProjectionInvoke = vi.fn();
vi.mock("@macrohero/tools/analytics", () => ({
  runFactorProjection: {
    name: "run_factor_projection",
    description: "stubbed",
    schema: { parse: (x: unknown) => x },
    invoke: mockProjectionInvoke,
  },
}));

const { makeAnalyticsSubagent } = await import("../../src/subagents/analytics.js");

describe("analytics subagent", () => {
  beforeEach(() => {
    mockProjectionInvoke.mockReset();
  });

  it("invokes run_factor_projection with structured args", async () => {
    mockProjectionInvoke.mockResolvedValue({
      pair: "EUR/USD",
      r_squared: 0.4,
      projection: { point_pct: 1.5 },
      diagnostics: { error: null, warnings: [] },
      factors: [],
    });

    const llmStub: any = {
      lc_runnable: true,
      _modelType: () => "chat",
      bindTools: () => llmStub,
      invoke: vi
        .fn()
        .mockResolvedValueOnce(
          new AIMessage({
            content: "",
            tool_calls: [
              {
                name: "run_factor_projection",
                args: {
                  pair: "EUR/USD",
                  horizon_days: 14,
                  factors: [{ name: "Brent crude", direction: "down", severity: "severe" }],
                },
                id: "call_1",
              },
            ],
          }),
        )
        .mockResolvedValueOnce(new AIMessage("EUR/USD up ~1.5%.")),
      stream: vi.fn(),
      withConfig: () => llmStub,
    };

    const agent = makeAnalyticsSubagent({ llm: llmStub });
    await agent.invoke({
      messages: [new HumanMessage("What if oil crashes?")],
    });

    // ToolNode calls `tool.invoke({ ...call, type: "tool_call" }, config)`, so
    // the structured args are nested under `args`.
    expect(mockProjectionInvoke).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "run_factor_projection",
        args: expect.objectContaining({
          pair: "EUR/USD",
          horizon_days: 14,
          factors: [
            expect.objectContaining({
              name: "Brent crude",
              direction: "down",
              severity: "severe",
            }),
          ],
        }),
      }),
      expect.anything(),
    );
  });
});
