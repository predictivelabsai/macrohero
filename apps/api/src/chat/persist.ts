import type { ChatPart } from "@macrohero/shared";

/** A subset of AI SDK v6 UIMessagePart that we recognize. */
type UIPart =
  | {
      type: "text";
      text: string;
      providerMetadata?: Record<string, unknown> | null;
    }
  | {
      type: "reasoning";
      text: string;
      providerMetadata?: Record<string, unknown> | null;
    }
  | {
      type: `tool-${string}`;
      state: "output-available" | "output-error" | string;
      input?: unknown;
      output?: unknown;
      toolCallId?: string;
      callProviderMetadata?: Record<string, unknown> | null;
      providerMetadata?: Record<string, unknown> | null;
    }
  | {
      type: `data-${string}`;
      data?: unknown;
      transient?: boolean;
    }
  | { type: string };

// Pull the multi-agent attribution out of providerMetadata. The streaming
// transform writes `{ macrohero: { agent } }`. AI SDK assembles text/reasoning
// chunks' providerMetadata onto the part directly, and tool chunks'
// providerMetadata onto `callProviderMetadata`.
function extractAgent(part: UIPart): string | undefined {
  const anyPart = part as {
    providerMetadata?: Record<string, unknown> | null;
    callProviderMetadata?: Record<string, unknown> | null;
  };
  const pm = anyPart.providerMetadata ?? anyPart.callProviderMetadata;
  const ns = pm?.["macrohero"] as Record<string, unknown> | undefined;
  const v = ns?.["agent"];
  return typeof v === "string" && v.length > 0 ? v : undefined;
}

/**
 * Translate AI SDK v6 UIMessage parts into the parts_jsonb shape the
 * Python service writes today. The FE's reload path reads parts_jsonb and
 * renders bubbles in order, so byte-compatibility with the Python shape
 * is required for the kinds the Python service knows about; the new
 * `agent` field is additive (optional, ignored by the Python reader).
 *
 * Drops:
 *   - data-session (transient)
 *   - data-session-update (transient)
 *   - unknown part types (defensive)
 */
export function uiPartsToJsonb(parts: ReadonlyArray<UIPart>): ChatPart[] {
  const out: ChatPart[] = [];
  for (const part of parts) {
    const agent = extractAgent(part);
    if (part.type === "text") {
      out.push({
        kind: "text",
        text: (part as { text: string }).text,
        ...(agent ? { agent } : {}),
      });
    } else if (part.type === "reasoning") {
      out.push({
        kind: "reasoning",
        text: (part as { text: string }).text,
        ...(agent ? { agent } : {}),
      });
    } else if (part.type.startsWith("tool-")) {
      const toolName = part.type.slice("tool-".length);
      const p = part as Extract<UIPart, { type: `tool-${string}` }>;
      const state =
        p.state === "output-error" ? "output-error" : "output-available";
      out.push({
        kind: "tool",
        tool_name: toolName,
        state,
        input: (p.input ?? null) as Record<string, unknown> | null,
        ...(agent ? { agent } : {}),
      });
    } else if (part.type === "data-scenario_projection") {
      const p = part as Extract<UIPart, { type: `data-${string}` }>;
      out.push({
        kind: "scenario_projection",
        // We trust the data shape — it came from our own numerics service.
        data: p.data as never,
      });
    }
    // All other types (data-session, data-session-update, unknown) drop through.
  }
  return out;
}

export function extractFinalText(parts: ReadonlyArray<UIPart>): string {
  return parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("");
}

export function extractFinalReasoning(parts: ReadonlyArray<UIPart>): string {
  return parts
    .filter((p): p is { type: "reasoning"; text: string } => p.type === "reasoning")
    .map((p) => p.text)
    .filter((t) => t.length > 0)
    .join("\n\n");
}
