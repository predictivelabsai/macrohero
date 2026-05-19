import { ChatDeepSeek } from "@langchain/deepseek";
import { isAIMessage, type BaseMessage } from "@langchain/core/messages";

export interface MakeLLMOptions {
  temperature?: number;
  model?: string;
}

/**
 * ChatDeepSeek + the missing piece of thinking-mode round-tripping.
 *
 * `@langchain/deepseek@0.1.0` reads `reasoning_content` from streamed chunks
 * into `additional_kwargs.reasoning_content`, but it does NOT echo it back
 * in subsequent request bodies. DeepSeek's thinking-mode API requires that
 * any assistant message carrying `reasoning_content` from a prior turn must
 * include it on the way back, or it returns:
 *
 *   400: the reasoning_content in the thinking mode must be passed back to the api
 *
 * The Python service handles this with `_install_deepseek_reasoning_outgoing()`
 * (api/src/macrohero/chat/agent.py) by monkey-patching `_convert_message_to_dict`.
 * Module-level monkey-patching doesn't work in ESM since the chat_models.js
 * call site uses a local lexical reference, so we subclass instead.
 *
 * Strategy: stash the original LangChain messages on `_generate` /
 * `_streamResponseChunks`, then in `completionWithRetry`, inject
 * `reasoning_content` onto each assistant entry in the already-serialized
 * `params.messages` from the corresponding `additional_kwargs.reasoning_content`.
 */
class ChatDeepSeekWithReasoning extends ChatDeepSeek {
  // Stashed per-call so we can correlate the serialized assistant entries
  // back to their LangChain originals (which still carry reasoning_content
  // in additional_kwargs). Agent calls serialize per LLM instance, so the
  // stash isn't shared across concurrent requests in practice.
  private _stashedOriginals: BaseMessage[] | null = null;

  private _withReasoning(
    serializedMessages: Array<Record<string, unknown>>,
  ): Array<Record<string, unknown>> {
    const originals = this._stashedOriginals;
    return serializedMessages.map((m, idx) => {
      if (m?.role !== "assistant") return m;
      // EVERY assistant message in a DeepSeek thinking-mode request must carry
      // a `reasoning_content` field — including SYNTHETIC ones (e.g., the
      // "Transferring back to supervisor" AIMessage that
      // @langchain/langgraph-supervisor injects after a subagent finishes).
      // Without it, the API returns:
      //   400: the reasoning_content in the thinking mode must be passed back
      //
      // For real ChatDeepSeek-generated turns we recover the reasoning from
      // the original LangChain message's additional_kwargs. For synthetic
      // turns we fall back to an empty string, which the API accepts.
      const orig = originals?.[idx];
      let rc: string | undefined;
      if (orig && isAIMessage(orig)) {
        const candidate = (orig.additional_kwargs as Record<string, unknown>)?.[
          "reasoning_content"
        ];
        if (typeof candidate === "string") rc = candidate;
      }
      return { ...m, reasoning_content: rc ?? "" };
    });
  }

  async _generate(messages: BaseMessage[], options: never, runManager: never): Promise<never> {
    this._stashedOriginals = messages;
    try {
      // @ts-expect-error super signature is internal
      return await super._generate(messages, options, runManager);
    } finally {
      this._stashedOriginals = null;
    }
  }

  async *_streamResponseChunks(
    messages: BaseMessage[],
    options: never,
    runManager: never,
  ): AsyncGenerator<never> {
    this._stashedOriginals = messages;
    try {
      // @ts-expect-error super signature is internal
      yield* super._streamResponseChunks(messages, options, runManager);
    } finally {
      this._stashedOriginals = null;
    }
  }

  // completionWithRetry is the unified call site for both streaming and
  // non-streaming requests. By this point messagesMapped has been built
  // by _convertMessagesToOpenAIParams and we can mutate it before the HTTP
  // request goes out.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async completionWithRetry(params: any, options?: any): Promise<any> {
    if (params && Array.isArray(params.messages)) {
      const patched = this._withReasoning(
        params.messages as Array<Record<string, unknown>>,
      );
      params = { ...params, messages: patched };
    }
    return super.completionWithRetry(params, options);
  }
}

export function makeLLM(opts: MakeLLMOptions = {}): ChatDeepSeek {
  const apiKey = process.env.DEEPSEEK_API_KEY ?? "";
  if (!apiKey) {
    throw new Error("DEEPSEEK_API_KEY is not set");
  }
  return new ChatDeepSeekWithReasoning({
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
  // DeepSeek's "flash" tier still runs in thinking mode by default; the
  // thinking pass eats tokens before any visible content is produced. With
  // maxTokens=80 (matching Python's max_completion_tokens=80) the thinking
  // budget exhausts the whole quota and nothing visible comes out. Use
  // modelKwargs to set max_completion_tokens (visible-only budget) AND a
  // generous overall max_tokens so the reasoning pass has room to finish.
  return new ChatDeepSeek({
    apiKey,
    model: process.env.DEEPSEEK_FLASH_MODEL ?? "deepseek-v4-flash",
    temperature: 0.1,
    streaming: false,
    modelKwargs: {
      max_completion_tokens: 80,
      max_tokens: 1024,
    },
  });
}
