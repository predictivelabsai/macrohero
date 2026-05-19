import {
  isAIMessage,
  isToolMessage,
  type AIMessage,
  type BaseMessage,
  type ToolMessage,
} from "@langchain/core/messages";

function isTransferToolName(name: unknown): boolean {
  return (
    typeof name === "string" &&
    (name.startsWith("transfer_to_") || name.startsWith("transfer_back_to_"))
  );
}

function isHandoffPlumbing(m: BaseMessage): boolean {
  if (isToolMessage(m)) {
    return isTransferToolName((m as ToolMessage).name);
  }
  if (isAIMessage(m)) {
    const tc = (m as AIMessage).tool_calls ?? [];
    if (tc.length === 0) return false;
    // An AIMessage whose only tool calls are handoffs is pure orchestration —
    // the supervisor (or a sub-agent on its way back) signaling a graph
    // transition. Sub-agents have no reason to see this; filtering it removes
    // the "I have been transferred to..." anchor that makes the model narrate
    // identity changes in its reasoning.
    return tc.every((c) => isTransferToolName(c.name));
  }
  return false;
}

/**
 * Remove `@langchain/langgraph-supervisor`'s handoff bookkeeping from a
 * message list. Strips:
 *   - ToolMessages named `transfer_to_*` or `transfer_back_to_*`
 *   - AIMessages whose tool_calls are exclusively transfer handoffs
 *
 * Applied per-call in each sub-agent's preModelHook (via `llmInputMessages`).
 * The persisted graph state stays untouched — only the LLM's view for this
 * call is cleaned. The goal is that each sub-agent's prompt looks like an
 * independent specialist receiving a question, not a node in a routing
 * machine that just got handed off to.
 */
export function stripHandoffPlumbing(messages: BaseMessage[]): BaseMessage[] {
  return messages.filter((m) => !isHandoffPlumbing(m));
}
