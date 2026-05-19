import { createUIMessageStream, createUIMessageStreamResponse } from "ai";
import {
  AIMessage,
  HumanMessage,
  makeSupervisor,
  transformLangGraphEvents,
  type BaseMessage,
  type StreamWriter,
} from "@macrohero/agent";
import { asc, eq } from "drizzle-orm";
import { chatMessages, chatSessions } from "@macrohero/db";
import { getDb } from "../db.js";
import {
  uiPartsToJsonb,
  extractFinalText,
  extractFinalReasoning,
} from "./persist.js";

/** History row read from chat_messages. */
export interface HistoryRow {
  role: "user" | "assistant" | string;
  content: string;
}

function toLangChainMessages(history: HistoryRow[]): BaseMessage[] {
  return history.map((m) =>
    m.role === "user" ? new HumanMessage(m.content) : new AIMessage(m.content),
  );
}

export interface StreamTurnOptions {
  sessionId: string;
  history: HistoryRow[];
  assistantOrdinal: number;
  /** Emitted before the agent runs. Used by /chat/start to publish the new session id. */
  prelude?: Array<Record<string, unknown>>;
  /**
   * If supplied, a fire-and-forget promise that resolves to a refreshed title
   * (or null). When it resolves before the stream ends, a data-session-update
   * chunk is written to the wire.
   */
  titleTask?: Promise<string | null>;
}

/**
 * Stream one assistant turn and persist it on completion. Returns a Response
 * with the AI SDK v6 UIMessage stream wire format. Callers in routes wrap this
 * with auth + DB session bookkeeping.
 */
export function streamTurn(opts: StreamTurnOptions): Response {
  const agent = makeSupervisor();
  const messages = toLangChainMessages(opts.history);

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      // Emit prelude chunks before the agent starts.
      if (opts.prelude) {
        for (const evt of opts.prelude) {
          writer.write(evt as never);
        }
      }

      // Title side-channel: fire-and-forget. If it resolves before execute
      // returns (kept alive by the await below), it writes data-session-update.
      const titleSideChannel = opts.titleTask
        ? opts.titleTask
            .then((newTitle) => {
              if (newTitle) {
                writer.write({
                  type: "data-session-update",
                  id: `sess_update_${opts.sessionId}`,
                  data: { sessionId: opts.sessionId, title: newTitle },
                  transient: true,
                } as never);
              }
            })
            .catch((err) => {
              console.warn("[streamTurn] title side-channel error:", err);
            })
        : null;

      // Run the agent. streamEvents emits structured LangGraph events.
      const upstream = agent.streamEvents(
        { messages },
        { version: "v2", recursionLimit: 25 },
      );

      // Drain the transformer. It writes ALL wire chunks (reasoning, text,
      // tool, scenario_projection) directly via writer.write — replacing
      // @ai-sdk/langchain's toUIMessageStream which (in v2) doesn't rotate
      // text ids across LLM calls and marks tools as dynamic.
      for await (const _ of transformLangGraphEvents(
        upstream,
        writer as unknown as StreamWriter,
      )) {
        // intentionally empty — side effects flow through writer.write
        void _;
      }

      // Keep execute alive until the title side-channel either lands or times
      // out, so a fast summarizer can write to a still-open writer. 20s
      // matches the Python implementation's wait_for shield.
      if (titleSideChannel) {
        await Promise.race([
          titleSideChannel,
          new Promise<void>((resolve) => setTimeout(resolve, 20_000)),
        ]);
      }
    },

    onFinish: async ({ responseMessage }) => {
      // responseMessage is the assistant turn (v6 callback signature).
      if (!responseMessage || responseMessage.role !== "assistant") return;

      const parts = (responseMessage.parts ?? []) as never[];
      const partsJsonb = uiPartsToJsonb(parts as never);
      const content = extractFinalText(parts as never);
      const reasoning = extractFinalReasoning(parts as never);

      const db = getDb();
      await db.insert(chatMessages).values({
        sessionId: opts.sessionId,
        ordinal: opts.assistantOrdinal,
        role: "assistant",
        content,
        reasoning,
        actionsJsonb: [],
        partsJsonb,
      });

      // Touch the session so updated_at advances and the sidebar resorts.
      await db
        .update(chatSessions)
        .set({ updatedAt: new Date() })
        .where(eq(chatSessions.id, opts.sessionId));
    },

    onError: (err) =>
      `Chat agent error: ${err instanceof Error ? err.message : String(err)}`,
  });

  // createUIMessageStreamResponse serializes the object-shaped UIMessage chunks
  // into the AI SDK v6 wire format (text/event-stream bytes) and returns a
  // Response. Without this serialization, Node's HTTP write() rejects the raw
  // object chunks with ERR_INVALID_ARG_TYPE.
  return createUIMessageStreamResponse({
    stream,
    headers: {
      "cache-control": "no-cache, no-transform",
      "x-vercel-ai-ui-message-stream": "v1",
    },
  });
}

/** Load history for a session, ordered by ordinal. */
export async function loadHistory(sessionId: string): Promise<HistoryRow[]> {
  const db = getDb();
  const rows = await db
    .select({ role: chatMessages.role, content: chatMessages.content })
    .from(chatMessages)
    .where(eq(chatMessages.sessionId, sessionId))
    .orderBy(asc(chatMessages.ordinal));
  return rows.map((r) => ({ role: r.role, content: r.content }));
}

/** Compute the next ordinal for a session. */
export async function nextOrdinal(sessionId: string): Promise<number> {
  const db = getDb();
  const rows = await db
    .select({ ordinal: chatMessages.ordinal })
    .from(chatMessages)
    .where(eq(chatMessages.sessionId, sessionId))
    .orderBy(asc(chatMessages.ordinal));
  if (rows.length === 0) return 0;
  return (rows[rows.length - 1]!.ordinal as number) + 1;
}
