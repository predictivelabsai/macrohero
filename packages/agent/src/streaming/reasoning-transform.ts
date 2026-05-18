import { randomUUID } from "node:crypto";

export interface StreamWriter {
  write(chunk: Record<string, unknown>): void;
}

export interface LangGraphEvent {
  event: string;
  name?: string;
  data?: {
    chunk?: {
      additional_kwargs?: { reasoning_content?: string };
      content?: unknown;
    };
    output?: unknown;
  };
}

function shortId(prefix: string): string {
  return `${prefix}_${randomUUID().slice(0, 12)}`;
}

/**
 * Yield every event from upstream unchanged. Side-effects:
 * - When a chat-model chunk carries reasoning_content, emit reasoning-start (on
 *   first occurrence), reasoning-delta (per chunk), and reasoning-end (once the
 *   stream ends).
 * - When run_factor_projection finishes, emit a data-scenario_projection
 *   custom part with the structured output.
 */
export async function* transformLangGraphEvents(
  upstream: AsyncIterable<LangGraphEvent>,
  writer: StreamWriter,
): AsyncIterable<LangGraphEvent> {
  let reasoningId: string | null = null;

  for await (const event of upstream) {
    if (event.event === "on_chat_model_stream") {
      const reasoning = event.data?.chunk?.additional_kwargs?.reasoning_content;
      if (typeof reasoning === "string" && reasoning.length > 0) {
        if (!reasoningId) {
          reasoningId = shortId("think");
          writer.write({ type: "reasoning-start", id: reasoningId });
        }
        writer.write({
          type: "reasoning-delta",
          id: reasoningId,
          delta: reasoning,
        });
      }
    }

    if (event.event === "on_tool_end" && event.name === "run_factor_projection") {
      writer.write({
        type: "data-scenario_projection",
        id: shortId("proj"),
        data: event.data?.output,
        transient: false,
      });
    }

    yield event;
  }

  if (reasoningId) {
    writer.write({ type: "reasoning-end", id: reasoningId });
  }
}
