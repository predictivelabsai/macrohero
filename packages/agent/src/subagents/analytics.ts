import { createReactAgent } from "@langchain/langgraph/prebuilt";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import { runFactorProjection } from "@macrohero/tools/analytics";
import { ANALYTICS_PROMPT } from "../prompts/analytics.js";
import { makeLLM } from "../llm.js";

export interface MakeAnalyticsSubagentOptions {
  llm?: BaseChatModel;
}

export function makeAnalyticsSubagent(opts: MakeAnalyticsSubagentOptions = {}) {
  return createReactAgent({
    llm: opts.llm ?? makeLLM({ temperature: 0.1 }),
    tools: [runFactorProjection],
    prompt: ANALYTICS_PROMPT,
    name: "analytics",
  });
}
