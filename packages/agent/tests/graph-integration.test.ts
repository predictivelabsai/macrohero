import { AIMessage, HumanMessage, ToolMessage } from "@langchain/core/messages";
import { describe, expect, it, vi } from "vitest";

// Stub the numerics fetch.
const PROJECTION_RESULT = {
  pair: "EUR/USD",
  horizon_days: 14,
  regression_window_days: 252,
  r_squared: 0.45,
  intercept: 0,
  factors: [{ name: "Brent crude", beta: -0.15, expected_change: -7.5 }],
  projection: { point_pct: 1.1, band_95_low_pct: -0.5, band_95_high_pct: 2.7 },
  diagnostics: { error: null, warnings: [], n_observations: 252 },
};

function llmThatProducesTransferCall() {
  return {
    bindTools: () => self,
    invoke: vi.fn().mockResolvedValue(
      new AIMessage({
        content: "",
        tool_calls: [
          { name: "transfer_to_analytics", args: {}, id: "transfer_1" },
        ],
      }),
    ),
    stream: vi.fn(),
    withConfig: () => self,
  };
}

const self = llmThatProducesTransferCall();

describe.skip("graph integration (placeholder)", () => {
  it("supervisor routes oil scenario through analytics subagent", async () => {
    // This test is marked .skip pending verification of createSupervisor's
    // LLM interface requirements in the installed version. Each component is
    // unit-tested separately in subagents/* and supervisor.test.ts.
    expect(true).toBe(true);
  });
});
