import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { SystemMessage, type BaseMessage } from "@langchain/core/messages";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import { runFactorProjection } from "@macrohero/tools/analytics";
import { ANALYTICS_PROMPT } from "../prompts/analytics.js";
import { makeLLM } from "../llm.js";
import { stripHandoffPlumbing } from "./handoff-filter.js";

export interface MakeAnalyticsSubagentOptions {
  llm?: BaseChatModel;
}

// See subagents/research.ts for the rationale on this hook shape.
const identityAnchorHook = (state: { messages: BaseMessage[] }) => ({
  llmInputMessages: [
    new SystemMessage(
      "You are an analytics specialist for factor-projection scenarios. " +
      "Read the scenario in the conversation below, translate it into the " +
      "structured factor shocks your tool expects, run the projection, and " +
      "produce a one-sentence result. Speak in the first person, but do " +
      "not narrate your role, do not refer to other agents or to a " +
      "supervisor, and do not frame your output as a hand-off or summary " +
      "for anyone.",
    ),
    ...stripHandoffPlumbing(state.messages),
  ],
});

export function makeAnalyticsSubagent(opts: MakeAnalyticsSubagentOptions = {}) {
  return createReactAgent({
    llm: opts.llm ?? makeLLM({ temperature: 0.1 }),
    tools: [runFactorProjection],
    prompt: ANALYTICS_PROMPT,
    preModelHook: identityAnchorHook,
    name: "analytics",
  });
}
