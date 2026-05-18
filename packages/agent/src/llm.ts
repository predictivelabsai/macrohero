import { ChatDeepSeek } from "@langchain/deepseek";

export interface MakeLLMOptions {
  temperature?: number;
  model?: string;
}

export function makeLLM(opts: MakeLLMOptions = {}): ChatDeepSeek {
  const apiKey = process.env.DEEPSEEK_API_KEY ?? "";
  if (!apiKey) {
    throw new Error("DEEPSEEK_API_KEY is not set");
  }
  return new ChatDeepSeek({
    apiKey,
    model: opts.model ?? process.env.DEEPSEEK_MODEL ?? "deepseek-v4-pro",
    temperature: opts.temperature ?? 0.2,
    streaming: true,
    modelKwargs: { parallel_tool_calls: false },
  });
}

export function makeFlashLLM(): ChatDeepSeek {
  const apiKey = process.env.DEEPSEEK_API_KEY ?? "";
  if (!apiKey) {
    throw new Error("DEEPSEEK_API_KEY is not set");
  }
  return new ChatDeepSeek({
    apiKey,
    model: process.env.DEEPSEEK_FLASH_MODEL ?? "deepseek-v4-flash",
    temperature: 0.1,
    maxTokens: 80,
    streaming: false,
  });
}
