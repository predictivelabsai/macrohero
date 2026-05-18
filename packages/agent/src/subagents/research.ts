import { createReactAgent } from "@langchain/langgraph/prebuilt";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import { searchCurrentEvents } from "@macrohero/tools/research";
import { RESEARCH_PROMPT } from "../prompts/research.js";
import { makeLLM } from "../llm.js";

export interface MakeResearchSubagentOptions {
  llm?: BaseChatModel;
}

export function makeResearchSubagent(opts: MakeResearchSubagentOptions = {}) {
  return createReactAgent({
    llm: opts.llm ?? makeLLM({ temperature: 0.2 }),
    tools: [searchCurrentEvents],
    prompt: RESEARCH_PROMPT,
    name: "research",
  });
}
