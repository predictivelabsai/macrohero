import { randomUUID } from "node:crypto";

export interface StreamWriter {
  write(chunk: Record<string, unknown>): void;
}

export interface LangGraphEvent {
  event: string;
  name?: string;
  run_id?: string;
  metadata?: Record<string, unknown>;
  data?: {
    chunk?: {
      additional_kwargs?: { reasoning_content?: string };
      content?: unknown;
      tool_call_chunks?: Array<{
        name?: string;
        args?: string;
        id?: string;
        index?: number;
      }>;
    };
    input?: unknown;
    output?: unknown;
  };
}

function shortId(prefix: string): string {
  return `${prefix}_${randomUUID().slice(0, 12)}`;
}

const NAME_CONTENT_RE = /<name>[^<]*<\/name>(?:<content>([^<]*)<\/content>)?/g;
function stripAgentNameWrap(text: string): string {
  return text.replace(NAME_CONTENT_RE, (_, inner) => inner ?? "");
}

function extractTextFromChunkContent(content: unknown): string {
  if (typeof content === "string") return stripAgentNameWrap(content);
  if (Array.isArray(content)) {
    return content
      .map((p) => {
        if (typeof p === "string") return p;
        if (
          p &&
          typeof p === "object" &&
          (p as { type?: unknown }).type === "text" &&
          typeof (p as { text?: unknown }).text === "string"
        ) {
          return (p as { text: string }).text;
        }
        return "";
      })
      .map(stripAgentNameWrap)
      .join("");
  }
  return "";
}

function unwrapToolOutput(raw: unknown): unknown {
  if (raw && typeof raw === "object" && typeof (raw as { content?: unknown }).content === "string") {
    try {
      return JSON.parse((raw as { content: string }).content);
    } catch {
      return raw;
    }
  }
  return raw;
}

function extractToolInput(event: LangGraphEvent): Record<string, unknown> {
  const data = event.data as { input?: unknown } | undefined;
  const input = data?.input;
  if (input && typeof input === "object") {
    const inner = (input as { input?: unknown }).input;
    if (inner && typeof inner === "object") return inner as Record<string, unknown>;
    return input as Record<string, unknown>;
  }
  return {};
}

const AGENT_NAMES = new Set(["supervisor", "research", "analytics"]);

function getAgent(event: LangGraphEvent): string | undefined {
  const md = event.metadata;
  if (!md) return undefined;

  const node = md["langgraph_node"];
  if (typeof node === "string" && AGENT_NAMES.has(node)) return node;

  const ns = md["langgraph_checkpoint_ns"];
  if (typeof ns === "string" && ns.length > 0) {
    for (const segment of ns.split("|")) {
      const name = segment.split(":")[0];
      if (name && AGENT_NAMES.has(name)) return name;
    }
  }

  const path = md["langgraph_path"];
  if (Array.isArray(path)) {
    for (const item of path) {
      if (typeof item === "string" && AGENT_NAMES.has(item)) return item;
    }
  }

  return undefined;
}

function agentProviderMetadata(agent: string | undefined): Record<string, unknown> | undefined {
  if (!agent) return undefined;
  return { macrohero: { agent } };
}

function extractToolCallsFromOutput(
  output: unknown,
): Array<{ id: string; name: string }> {
  if (!output || typeof output !== "object") return [];
  const tc = (output as { tool_calls?: unknown }).tool_calls;
  if (!Array.isArray(tc)) return [];
  const out: Array<{ id: string; name: string }> = [];
  for (const c of tc) {
    if (!c || typeof c !== "object") continue;
    const id = (c as { id?: unknown }).id;
    const name = (c as { name?: unknown }).name;
    if (typeof id === "string" && typeof name === "string") {
      out.push({ id, name });
    }
  }
  return out;
}

/**
 * Drive the AI SDK v6 UIMessage stream wire format from LangGraph's
 * streamEvents output.
 *
 * Tool-call lifecycle (matches AI SDK v6):
 *   - `tool-input-start { toolCallId, toolName }` is emitted the moment the
 *     LLM begins streaming a tool call (i.e., the first `tool_call_chunks`
 *     entry with a name). The FE renders the pill in `input-streaming` state
 *     immediately, so "Routing to research agent..." appears during the
 *     window the model is writing the tool name + args — replacing what was
 *     previously a three-dots idle gap.
 *   - `tool-input-available { toolCallId, toolName, input }` follows on
 *     `on_tool_start` (the graph's tool node is about to run). The pill
 *     transitions to `input-available`.
 *   - `tool-output-available { toolCallId, output }` follows on `on_tool_end`.
 *     The pill transitions to `output-available` ("Routed to ...").
 *
 * Identity: the AI SDK requires the same `toolCallId` across all four
 * lifecycle chunks to keep them on the same part. The LLM provides a stable
 * id on `tool_call_chunks` (e.g., `call_abc123`); LangGraph emits its own
 * `run_id` for the tool's runnable invocation. To bridge:
 *   - We use the LLM's id directly for `tool-input-start` (read off the chunk).
 *   - On `on_chat_model_end` we buffer `output.tool_calls` (id + name pairs).
 *   - On `on_tool_start` we match the next pending tool_call by name (FIFO)
 *     and use that id for `tool-input-available`. We also remember the
 *     run_id -> tool_call_id mapping for the matching `on_tool_end`.
 *
 * Multi-agent attribution:
 *   - `providerMetadata: { macrohero: { agent } }` is set on text-start,
 *     reasoning-start, tool-input-start, tool-input-available. Agent name is
 *     derived from `metadata.langgraph_checkpoint_ns` (first segment matching
 *     a known agent name).
 */
export async function* transformLangGraphEvents(
  upstream: AsyncIterable<LangGraphEvent>,
  writer: StreamWriter,
): AsyncIterable<LangGraphEvent> {
  let reasoningId: string | null = null;
  let textId: string | null = null;

  // tool_call_ids we've already emitted `tool-input-start` for. Subsequent
  // chunks with the same id are just args deltas — skip them (we don't render
  // streaming args inline).
  const startedToolCallIds = new Set<string>();
  // Buffered tool_calls from on_chat_model_end's AIMessage.tool_calls — used
  // to look up the LLM's tool_call_id when on_tool_start fires for a given
  // tool name. FIFO per name.
  const pendingToolCalls: Array<{ id: string; name: string }> = [];
  // LangGraph run_id -> LLM tool_call_id, populated at on_tool_start and
  // consumed at on_tool_end.
  const runIdToToolCallId = new Map<string, string>();

  const closeReasoning = (): void => {
    if (!reasoningId) return;
    writer.write({ type: "reasoning-end", id: reasoningId });
    reasoningId = null;
  };

  const closeText = (): void => {
    if (!textId) return;
    writer.write({ type: "text-end", id: textId });
    textId = null;
  };

  for await (const event of upstream) {
    const agent = getAgent(event);
    const pm = agentProviderMetadata(agent);

    if (event.event === "on_chat_model_start") {
      closeReasoning();
      closeText();
    }

    if (event.event === "on_chat_model_stream") {
      const reasoning = event.data?.chunk?.additional_kwargs?.reasoning_content;
      const text = extractTextFromChunkContent(event.data?.chunk?.content);
      const toolCallChunks = event.data?.chunk?.tool_call_chunks;

      if (typeof reasoning === "string" && reasoning.length > 0) {
        closeText();
        if (!reasoningId) {
          reasoningId = shortId("think");
          writer.write({
            type: "reasoning-start",
            id: reasoningId,
            ...(pm ? { providerMetadata: pm } : {}),
          });
        }
        writer.write({
          type: "reasoning-delta",
          id: reasoningId,
          delta: reasoning,
        });
      } else if (text.length > 0) {
        closeReasoning();
        if (!textId) {
          textId = shortId("txt");
          writer.write({
            type: "text-start",
            id: textId,
            ...(pm ? { providerMetadata: pm } : {}),
          });
        }
        writer.write({ type: "text-delta", id: textId, delta: text });
      }

      // The model is committing to a tool call — emit `tool-input-start` so
      // the pill renders during the args-streaming window instead of an idle
      // gap. Only fire once per tool_call_id; subsequent chunks are arg
      // deltas (we don't render those).
      if (Array.isArray(toolCallChunks)) {
        for (const c of toolCallChunks) {
          const id = c?.id;
          const name = c?.name;
          if (
            typeof id === "string" &&
            typeof name === "string" &&
            id.length > 0 &&
            !startedToolCallIds.has(id)
          ) {
            startedToolCallIds.add(id);
            // Also close any open text/reasoning bubble — once the model is
            // writing a tool call, prose for this LLM call is done.
            closeReasoning();
            closeText();
            writer.write({
              type: "tool-input-start",
              toolCallId: id,
              toolName: name,
              ...(pm ? { providerMetadata: pm } : {}),
            });
          }
        }
      }
    }

    if (event.event === "on_chat_model_end") {
      closeReasoning();
      closeText();
      // Buffer this call's tool_calls so the upcoming on_tool_start can find
      // the right LLM-issued tool_call_id by name.
      for (const tc of extractToolCallsFromOutput(event.data?.output)) {
        pendingToolCalls.push(tc);
      }
    }

    if (event.event === "on_tool_start") {
      const runId = event.run_id;
      const name = event.name;
      if (runId && name) {
        const idx = pendingToolCalls.findIndex((p) => p.name === name);
        const toolCallId =
          idx >= 0 ? pendingToolCalls.splice(idx, 1)[0]!.id : runId;
        runIdToToolCallId.set(runId, toolCallId);
        writer.write({
          type: "tool-input-available",
          toolCallId,
          toolName: name,
          input: extractToolInput(event),
          ...(pm ? { providerMetadata: pm } : {}),
        });
      }
    }

    if (event.event === "on_tool_end") {
      const runId = event.run_id;
      const output = unwrapToolOutput(event.data?.output);
      if (runId) {
        const toolCallId = runIdToToolCallId.get(runId) ?? runId;
        runIdToToolCallId.delete(runId);
        writer.write({
          type: "tool-output-available",
          toolCallId,
          output,
        });
      }

      if (event.name === "run_factor_projection") {
        writer.write({
          type: "data-scenario_projection",
          id: shortId("proj"),
          data: output,
          transient: false,
        });
      }
    }

    yield event;
  }

  closeReasoning();
  closeText();
}
