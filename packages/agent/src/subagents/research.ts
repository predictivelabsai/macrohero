import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { SystemMessage, type BaseMessage } from "@langchain/core/messages";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import { searchCurrentEvents } from "@macrohero/tools/research";
import { RESEARCH_PROMPT } from "../prompts/research.js";
import { makeLLM } from "../llm.js";
import { stripHandoffPlumbing } from "./handoff-filter.js";

export interface MakeResearchSubagentOptions {
  llm?: BaseChatModel;
}

// Runs before every LLM call inside the research react-agent. Returns
// `llmInputMessages` (not `messages`), so it shapes what the LLM sees this
// call without growing the persisted log.
//
// Two jobs:
//   1. Strip handoff plumbing (`transfer_to_*` ToolMessages + the
//      orchestration-only AIMessages that triggered them). This removes the
//      "Successfully transferred to research" anchor that otherwise prompts
//      the model to narrate identity transitions in its chain-of-thought.
//   2. Prepend a fresh identity-anchor SystemMessage that frames the call as
//      an independent specialist receiving a question — no multi-agent
//      framing, no peer-agent references.
const identityAnchorHook = (state: { messages: BaseMessage[] }) => ({
  llmInputMessages: [
    new SystemMessage(
      "You are a research specialist. Read the question in the conversation " +
      "below and produce a focused factual finding. Speak in the first " +
      "person, but do not narrate your role, do not refer to other agents " +
      "or to a supervisor, and do not frame your output as a hand-off or " +
      "summary for anyone. Just think about the substance of the question " +
      "and write the finding.",
    ),
    ...stripHandoffPlumbing(state.messages),
  ],
});

export function makeResearchSubagent(opts: MakeResearchSubagentOptions = {}) {
  return createReactAgent({
    llm: opts.llm ?? makeLLM({ temperature: 0.2 }),
    tools: [searchCurrentEvents],
    prompt: RESEARCH_PROMPT,
    preModelHook: identityAnchorHook,
    name: "research",
  });
}
