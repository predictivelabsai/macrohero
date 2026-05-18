import { createSupervisor } from "@langchain/langgraph-supervisor";
import type { BaseChatModel } from "@langchain/core/language_models/chat_models";
import { makeAnalyticsSubagent } from "./subagents/analytics.js";
import { makeResearchSubagent } from "./subagents/research.js";
import { SUPERVISOR_PROMPT } from "./prompts/supervisor.js";
import { makeLLM } from "./llm.js";

export interface MakeSupervisorOptions {
  llm?: BaseChatModel;
  /** Override subagent constructors — used by tests. */
  researchSubagent?: ReturnType<typeof makeResearchSubagent>;
  analyticsSubagent?: ReturnType<typeof makeAnalyticsSubagent>;
}

export function makeSupervisor(opts: MakeSupervisorOptions = {}) {
  const research = opts.researchSubagent ?? makeResearchSubagent({ llm: opts.llm });
  const analytics = opts.analyticsSubagent ?? makeAnalyticsSubagent({ llm: opts.llm });

  return createSupervisor({
    agents: [research, analytics],
    llm: opts.llm ?? makeLLM(),
    prompt: SUPERVISOR_PROMPT,
  }).compile();
}
