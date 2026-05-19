import { describe, expect, it } from "vitest";
import {
  AIMessage,
  HumanMessage,
  SystemMessage,
  ToolMessage,
} from "@langchain/core/messages";
import { stripHandoffPlumbing } from "../../src/subagents/handoff-filter.js";

describe("stripHandoffPlumbing", () => {
  it("drops `transfer_to_*` ToolMessages", () => {
    const messages = [
      new HumanMessage("question"),
      new ToolMessage({
        content: "Successfully transferred to research",
        name: "transfer_to_research",
        tool_call_id: "call_1",
      }),
    ];
    expect(stripHandoffPlumbing(messages)).toHaveLength(1);
    expect(stripHandoffPlumbing(messages)[0]).toBeInstanceOf(HumanMessage);
  });

  it("drops `transfer_back_to_*` ToolMessages and their AIMessage", () => {
    const messages = [
      new HumanMessage("question"),
      new AIMessage({
        content: "Transferring back to supervisor",
        tool_calls: [{ name: "transfer_back_to_supervisor", args: {}, id: "id1" }],
        name: "research",
      }),
      new ToolMessage({
        content: "Successfully transferred back to supervisor",
        name: "transfer_back_to_supervisor",
        tool_call_id: "id1",
      }),
    ];
    expect(stripHandoffPlumbing(messages)).toHaveLength(1);
  });

  it("drops AIMessages whose ONLY tool calls are handoffs", () => {
    const messages = [
      new HumanMessage("question"),
      new AIMessage({
        content: "",
        tool_calls: [{ name: "transfer_to_research", args: {}, id: "id1" }],
      }),
    ];
    expect(stripHandoffPlumbing(messages)).toHaveLength(1);
  });

  it("keeps AIMessages with non-handoff tool calls", () => {
    const messages = [
      new HumanMessage("question"),
      new AIMessage({
        content: "Searching...",
        tool_calls: [{ name: "search_current_events", args: { query: "x" }, id: "id1" }],
      }),
    ];
    expect(stripHandoffPlumbing(messages)).toHaveLength(2);
  });

  it("keeps substantive AIMessages with no tool calls (peer agent findings)", () => {
    const messages = [
      new HumanMessage("question"),
      new AIMessage({ content: "the finding", name: "research" }),
    ];
    expect(stripHandoffPlumbing(messages)).toHaveLength(2);
  });

  it("keeps non-transfer ToolMessages (search results, projection outputs)", () => {
    const messages = [
      new HumanMessage("question"),
      new ToolMessage({
        content: "search results...",
        name: "search_current_events",
        tool_call_id: "call_1",
      }),
    ];
    expect(stripHandoffPlumbing(messages)).toHaveLength(2);
  });

  it("preserves message order for non-stripped entries", () => {
    const messages = [
      new SystemMessage("sys"),
      new HumanMessage("question"),
      new AIMessage({
        content: "",
        tool_calls: [{ name: "transfer_to_research", args: {}, id: "id1" }],
      }),
      new ToolMessage({
        content: "Successfully transferred to research",
        name: "transfer_to_research",
        tool_call_id: "id1",
      }),
      new AIMessage({ content: "research finding", name: "research" }),
    ];
    const out = stripHandoffPlumbing(messages);
    expect(out).toHaveLength(3);
    expect(out[0]).toBeInstanceOf(SystemMessage);
    expect(out[1]).toBeInstanceOf(HumanMessage);
    expect(out[2]).toBeInstanceOf(AIMessage);
    expect((out[2] as AIMessage).content).toBe("research finding");
  });
});
