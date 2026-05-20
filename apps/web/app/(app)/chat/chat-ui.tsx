"use client";

/* eslint-disable react-hooks/refs --
 * The React Compiler rule can't tell that sessionIdRef is read from inside
 * a request callback (prepareSendMessagesRequest), not during render.
 */

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Markdown } from "@/components/markdown";
import { ScenarioCard } from "@/components/scenario-card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ProjectionResult } from "@/lib/scenarios";

export type ChatAction = {
  type: string;
  id: string;
  title: string;
  url: string;
};

export type ChatMessagePart =
  | { kind: "reasoning"; text: string; agent?: string }
  | { kind: "text"; text: string; agent?: string }
  | {
      kind: "tool";
      tool_name: string;
      state?: "output-available" | "output-error";
      input?: Record<string, unknown>;
      action_id?: string | null;
      agent?: string;
    }
  | { kind: "scenario_projection"; data: ProjectionResult };

export type InitialMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning: string;
  actions: ChatAction[];
  parts: ChatMessagePart[];
};

const PROMPT_HINTS: Array<{ icon: string; text: string }> = [
  {
    icon: "🛢️",
    text: "If the Hormuz conflict de-escalates in the next two weeks, how should USD/CAD trend?",
  },
  {
    icon: "🏛️",
    text: "The Fed surprises with a dovish pivot in December — where does EUR/USD trade by Q1?",
  },
  {
    icon: "🚢",
    text: "China retaliates with new tariffs on US goods. What happens to AUD/USD over the next month?",
  },
  {
    icon: "📉",
    text: "Sudden risk-off after a credit event in private credit — how does USD/JPY react?",
  },
];

export function ChatUI({
  sessionId,
  initialMessages,
  displayName,
  greeting,
  showThinking = false,
}: {
  sessionId: string | null;
  initialMessages: InitialMessage[];
  displayName?: string | null;
  greeting?: string;
  showThinking?: boolean;
}) {
  const router = useRouter();
  const [input, setInput] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string | null>(sessionId);

  const [initial] = useState<UIMessage[]>(() =>
    initialMessages.map((m) => {
      const parts: UIMessage["parts"] = [];
      if (m.parts.length > 0) {
        for (const p of m.parts) {
          // Re-attach the agent attribution that the streaming layer
          // recorded under providerMetadata.macrohero.agent. For tools the
          // AI SDK exposes this on `callProviderMetadata`; for text and
          // reasoning it's on `providerMetadata`. Same shape either way.
          const agentMeta = p.kind !== "scenario_projection" && p.agent
            ? { macrohero: { agent: p.agent } }
            : undefined;
          if (p.kind === "reasoning" && p.text) {
            parts.push({
              type: "reasoning",
              text: p.text,
              state: "done",
              ...(agentMeta ? { providerMetadata: agentMeta } : {}),
            } as UIMessage["parts"][number]);
          } else if (p.kind === "text" && p.text) {
            parts.push({
              type: "text",
              text: p.text,
              ...(agentMeta ? { providerMetadata: agentMeta } : {}),
            } as UIMessage["parts"][number]);
          } else if (p.kind === "tool") {
            // Re-emit as a tool-${name} part with state already "output-available"
            // so the pill renders as "complete" on history reload.
            parts.push({
              type: `tool-${p.tool_name}`,
              state: p.state ?? "output-available",
              input: p.input ?? {},
              ...(agentMeta ? { callProviderMetadata: agentMeta } : {}),
            } as unknown as UIMessage["parts"][number]);
          } else if (p.kind === "scenario_projection") {
            parts.push({
              type: "data-scenario_projection",
              data: p.data,
            } as UIMessage["parts"][number]);
          }
        }
      } else {
        if (m.reasoning) {
          parts.push({
            type: "reasoning",
            text: m.reasoning,
            state: "done",
          } as UIMessage["parts"][number]);
        }
        if (m.content) {
          parts.push({ type: "text", text: m.content });
        }
      }
      return { id: m.id, role: m.role, parts };
    }),
  );

  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/chat/start",
        prepareSendMessagesRequest: ({ messages }) => {
          const last = [...messages].reverse().find((m) => m.role === "user");
          const text =
            last?.parts
              ?.filter((p): p is { type: "text"; text: string } => p.type === "text")
              .map((p) => p.text)
              .join("") ?? "";
          const currentId = sessionIdRef.current;
          return {
            body: { content: text },
            api: currentId ? `/api/chat/${currentId}` : "/api/chat/start",
          };
        },
      }),
    [],
  );

  const { messages, sendMessage, status, error } = useChat({
    id: sessionId ?? "new",
    messages: initial,
    transport,
    onData: (part) => {
      if (part.type === "data-session") {
        // Capture the new session id but DON'T refresh yet — a refresh here
        // would pull the placeholder title into the sidebar before the LLM
        // summarizer has had a chance to overwrite it. The sidebar refresh
        // is deferred to `data-session-update` (or `onFinish` as fallback)
        // so the first time the new entry appears it already has the proper
        // summarized title.
        const data = part.data as { sessionId?: string } | undefined;
        if (data?.sessionId) {
          sessionIdRef.current = data.sessionId;
        }
      } else if (part.type === "data-session-update") {
        // Emitted by the backend once the LLM title summarizer finishes
        // (near the end of the assistant turn). The new title is already
        // persisted; we just need to re-render the sidebar.
        router.refresh();
      }
    },
    onFinish: () => {
      const currentId = sessionIdRef.current;
      if (currentId && currentId !== sessionId) {
        router.replace(`/chat/${currentId}`, { scroll: false });
      }
      // Always refresh — picks up the LLM-summarized title in the sidebar
      // when the summarizer succeeded but `data-session-update` hasn't yet
      // fired (rare race), and also ensures the sidebar shows the new chat
      // entry when the summarizer failed and no update event was emitted.
      router.refresh();
    },
  });

  const isStreaming = status === "submitted" || status === "streaming";

  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isStreaming]);

  const submit = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    sendMessage({ text: trimmed });
    setInput("");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      {/* scrollbar-gutter:stable reserves the 10px gutter on desktop (matches
          our ::-webkit-scrollbar width in globals.css), paired with sm:pr-[10px]
          on the composer wrapper below so max-w-3xl content aligns on both
          edges regardless of whether the scrollbar is currently visible. On
          mobile the scrollbar is an overlay (zero width), so we drop the
          gutter and the matching pr — otherwise the composer ends 10px shy
          of the message bubbles' right edge. */}
      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto sm:[scrollbar-gutter:stable]"
      >
        <div className="mx-auto w-full max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
          {empty ? (
            <EmptyState
              onPick={(text) => sendMessage({ text })}
              displayName={displayName}
              greeting={greeting}
            />
          ) : (
            <div className="space-y-6">
              {messages.map((m, i) => (
                <MessageBubble
                  key={m.id}
                  message={m}
                  isStreaming={isStreaming && i === messages.length - 1}
                  showThinking={showThinking}
                />
              ))}
              {isStreaming && messages[messages.length - 1]?.role !== "assistant" && (
                <ThinkingBubble />
              )}
              {error && <ErrorBubble text={error.message} />}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border/40 bg-background/40 backdrop-blur sm:pr-[10px]">
        <div className="mx-auto w-full max-w-3xl px-4 py-3 sm:px-6 sm:py-4">
          {/* Unified composer surface — textarea sits flat inside a single
              rounded card; focus glow lives on the wrapper, not the input,
              so we don't get a clashing inner ring on top of an outer
              border. Send button is overlaid in the bottom-right corner. */}
          <div className="group relative rounded-2xl border border-border/70 bg-card/60 backdrop-blur-xl transition-all focus-within:border-primary/50 focus-within:bg-card/80 focus-within:shadow-[0_0_0_3px_oklch(0.72_0.2_235/0.12)]">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Message MacroHero..."
              disabled={isStreaming}
              rows={2}
              className="!min-h-[64px] resize-none !border-0 !bg-transparent px-4 pt-3 pb-12 text-sm !shadow-none !outline-none focus-visible:!ring-0"
              autoFocus
            />
            <div className="pointer-events-none absolute right-2 bottom-2">
              <Button
                onClick={submit}
                disabled={!input.trim() || isStreaming}
                size="sm"
                className="pointer-events-auto h-8 px-3 font-mono text-xs tracking-wider uppercase"
              >
                {isStreaming ? "Sending" : "Send"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({
  onPick,
  displayName,
  greeting,
}: {
  onPick: (text: string) => void;
  displayName?: string | null;
  greeting?: string;
}) {
  const heading = greeting
    ? displayName
      ? `${greeting}, ${displayName}.`
      : `${greeting}.`
    : "Describe a macro scenario.";
  return (
    <div className="mx-auto flex max-w-2xl flex-col py-12">
      <div className="text-center">
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary">
          FX scenario analysis
        </span>
        <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
          {heading}
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Describe a macro scenario in plain language — geopolitics, central banks, or market
          shocks. MacroHero maps it to historical drivers and projects the FX response.
        </p>
      </div>
      <div className="mt-8 grid w-full gap-2 sm:grid-cols-2">
        {PROMPT_HINTS.map((h) => (
          <button
            key={h.text}
            type="button"
            onClick={() => onPick(h.text)}
            className="flex items-start gap-3 rounded-lg border border-border bg-background px-4 py-3 text-left text-sm transition-colors hover:border-primary/60 hover:bg-muted"
          >
            <span className="shrink-0 text-base">{h.icon}</span>
            <span className="leading-snug">{h.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  isStreaming,
  showThinking,
}: {
  message: UIMessage;
  isStreaming: boolean;
  showThinking: boolean;
}) {
  if (message.role === "user") {
    const text = message.parts
      .filter((p): p is { type: "text"; text: string } => p.type === "text")
      .map((p) => p.text)
      .join("");
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md border border-primary/30 bg-primary/10 px-4 py-2.5 text-sm whitespace-pre-wrap text-foreground backdrop-blur-sm">
          {text}
        </div>
      </div>
    );
  }

  return (
    <AssistantBubble
      message={message}
      isStreaming={isStreaming}
      showThinking={showThinking}
    />
  );
}

// AI SDK v6 attaches custom providerMetadata under a namespace key. We use
// `macrohero.agent` for text/reasoning (via `providerMetadata`) and the same
// shape via `callProviderMetadata` on tool parts.
function readPartAgent(p: {
  providerMetadata?: Record<string, unknown> | null;
  callProviderMetadata?: Record<string, unknown> | null;
}): string | undefined {
  const pm = p.providerMetadata ?? p.callProviderMetadata;
  const ns = pm?.["macrohero"];
  if (ns && typeof ns === "object") {
    const v = (ns as { agent?: unknown }).agent;
    if (typeof v === "string" && v.length > 0) return v;
  }
  return undefined;
}

function AssistantBubble({
  message,
  isStreaming,
  showThinking,
}: {
  message: UIMessage;
  isStreaming: boolean;
  showThinking: boolean;
}) {
  type AnyPart = {
    type: string;
    id?: string;
    toolCallId?: string;
    text?: string;
    state?: string;
    data?: ProjectionResult;
    input?: { query?: string } & Record<string, unknown>;
    output?: unknown;
    providerMetadata?: Record<string, unknown> | null;
    callProviderMetadata?: Record<string, unknown> | null;
  };
  const renderedParts = (message.parts as unknown as AnyPart[]).filter(
    (p) =>
      p.type === "text" ||
      p.type === "reasoning" ||
      p.type === "data-scenario_projection" ||
      p.type.startsWith("tool-"),
  );

  // Idle detector: when streaming but nothing new has arrived for ~700ms,
  // show a Dots placeholder under the last text/reasoning part. This fills
  // the gap when the model has stopped emitting prose and is silently
  // streaming tool-call args (before the tool pill appears). The reset
  // happens in the effect's cleanup so we don't call setState in the body.
  const contentLen = message.parts.reduce((sum, p) => {
    const text = (p as unknown as { text?: string }).text;
    return sum + (typeof text === "string" ? text.length : 0);
  }, 0);
  const partsCount = message.parts.length;
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    if (!isStreaming) return undefined;
    const t = setTimeout(() => setIdle(true), 700);
    return () => {
      clearTimeout(t);
      setIdle((curr) => (curr ? false : curr));
    };
  }, [isStreaming, contentLen, partsCount]);

  const lastPart = renderedParts[renderedParts.length - 1];
  // Suppress dots when the last visible thing is a tool pill that's still
  // running (state input-streaming or input-available) — that pill is
  // already showing a spinner. After the pill completes (output-available)
  // OR after a text/reasoning bubble, an idle gap before the next chunk
  // (e.g., between "Routed to research agent" and research's first reasoning
  // chunk) deserves dots so the user knows work is still ongoing.
  const lastPartIsRunningPill =
    !!lastPart &&
    lastPart.type.startsWith("tool-") &&
    lastPart.state !== "output-available" &&
    lastPart.state !== "output-error";
  const showDotsPlaceholder =
    isStreaming && (renderedParts.length === 0 || (idle && !lastPartIsRunningPill));

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[85%] space-y-2">
        {renderedParts.map((p, i) => {
          const key = `part-${i}`;
          const agent = readPartAgent(p);
          if (p.type === "text") {
            if (!p.text) return null;
            // A sub-agent's text is its report back to the supervisor — i.e.
            // inter-agent communication. With "show thinking" off we replace it
            // with a compact "communicating with" line (collapsing consecutive
            // chunks of the same specialist's reply into one).
            if (!showThinking && agent && agent !== "supervisor") {
              const prev = renderedParts[i - 1];
              if (prev?.type === "text" && readPartAgent(prev) === agent) return null;
              return <AgentCommLine key={key} from={agent} />;
            }
            return <TextBubble key={key} text={p.text} agent={agent} />;
          }
          if (p.type === "reasoning") {
            if (!p.text) return null;
            // Reasoning is "thought process" for EVERY agent. It always renders;
            // ReasoningBlock collapses it by default when thinking is off.
            const isLive = isStreaming && p.state !== "done";
            return (
              <ReasoningBlock
                key={key}
                text={p.text}
                streaming={isLive}
                agent={agent}
                showThinking={showThinking}
              />
            );
          }
          if (p.type === "data-scenario_projection" && p.data) {
            return <ScenarioCard key={key} data={p.data} />;
          }
          if (p.type.startsWith("tool-")) {
            return <ToolPill key={key} part={p} agent={agent} showThinking={showThinking} />;
          }
          return null;
        })}
        {showDotsPlaceholder && <Dots />}
      </div>
    </div>
  );
}

const AGENT_LABEL: Record<string, string> = {
  supervisor: "Supervisor",
  research: "Research",
  analytics: "Analytics",
};

function agentLabel(agent: string): string {
  return AGENT_LABEL[agent] ?? agent.charAt(0).toUpperCase() + agent.slice(1);
}

function AgentBadge({ agent }: { agent: string }) {
  return (
    <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground/80">
      {agentLabel(agent)}
    </span>
  );
}

// Compact stand-in for a specialist's report back to the supervisor, shown when
// "show thinking" is off. Mirrors the relabeled transfer pill (supervisor →
// specialist) for the reverse direction (specialist → supervisor).
function AgentCommLine({ from }: { from: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="inline-flex items-center gap-2 self-start rounded-full border border-border/60 bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
        <ToolDoneIcon kind="agent" />
        <span>{agentLabel(from)} agent communicating with Supervisor</span>
      </div>
    </div>
  );
}

// Primary bubble for the supervisor's text — already visually distinct from
// the rounded card; no badge needed. Sub-agent text (research / analytics)
// renders as a muted indented bubble with a smaller font + agent badge,
// visually clearly NOT the final answer.
function TextBubble({
  text,
  agent,
}: {
  text: string;
  agent: string | undefined;
}) {
  const isPrimary = !agent || agent === "supervisor";
  if (isPrimary) {
    return (
      <div className="rounded-2xl rounded-bl-md border border-border/60 bg-card/50 px-4 py-3 text-foreground backdrop-blur-sm">
        <Markdown>{text}</Markdown>
      </div>
    );
  }
  return (
    <div className="ml-4 border-l-2 border-border/50 pb-2 pl-3 text-muted-foreground opacity-80">
      <div className="mb-1">
        <AgentBadge agent={agent} />
      </div>
      <Markdown className="text-xs">{text}</Markdown>
    </div>
  );
}

const TOOL_PILL_CONFIG: Record<string, { running: string; done: string; icon: "search" | "chart" | "agent" }> = {
  "tool-search_current_events": {
    running: "Searching the web for current context",
    done: "Web search complete",
    icon: "search",
  },
  "tool-run_factor_projection": {
    running: "Running the scenario projection",
    done: "Projection complete",
    icon: "chart",
  },
  "tool-transfer_to_research": {
    running: "Routing to research agent",
    done: "Routed to research agent",
    icon: "agent",
  },
  "tool-transfer_to_analytics": {
    running: "Routing to analytics agent",
    done: "Routed to analytics agent",
    icon: "agent",
  },
};

/**
 * Strip the `tool-` prefix and humanize the rest as a fallback label.
 * Used for any tool that doesn't have an entry in TOOL_PILL_CONFIG —
 * prevents new tools from silently disappearing.
 */
function fallbackToolLabel(toolType: string): string {
  return toolType.replace(/^tool-/, "").replace(/_/g, " ");
}

function ToolPill({
  part,
  agent,
  showThinking,
}: {
  part: {
    type: string;
    state?: string;
    input?: { query?: string } & Record<string, unknown>;
  };
  agent: string | undefined;
  showThinking: boolean;
}) {
  const config = TOOL_PILL_CONFIG[part.type];
  const done = part.state === "output-available";
  const errored = part.state === "output-error";
  const running = !done && !errored;
  const fallbackName = !config ? fallbackToolLabel(part.type) : null;
  // With "show thinking" off, the supervisor→sub-agent handoff is summarized as
  // a single "communicating with" line instead of the routing/messages.
  const transferTarget = part.type.startsWith("tool-transfer_to_")
    ? part.type.replace("tool-transfer_to_", "")
    : null;
  const communicatingLabel =
    !showThinking && !errored && transferTarget
      ? `Supervisor communicating with ${agentLabel(transferTarget)} agent`
      : null;
  const label = communicatingLabel
    ? communicatingLabel
    : errored
      ? "Tool error"
      : config
        ? running ? config.running : config.done
        : running ? `Running ${fallbackName}` : `${fallbackName} complete`;
  const icon = config?.icon ?? "agent";
  // Show the search query inline as additional context once we have it.
  const query =
    part.type === "tool-search_current_events" && typeof part.input?.query === "string"
      ? part.input.query
      : null;
  return (
    <div className="flex items-center gap-2">
      <div className="inline-flex items-center gap-2 self-start rounded-full border border-border/60 bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
        {running ? (
          <Spinner />
        ) : errored ? (
          <span className="text-destructive">!</span>
        ) : (
          <ToolDoneIcon kind={icon} />
        )}
        <span>{label}</span>
        {query && (
          <span className="font-mono text-muted-foreground/80">
            “{query.length > 60 ? query.slice(0, 60) + "…" : query}”
          </span>
        )}
        {agent && !communicatingLabel && (
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground/60">
            · {agentLabel(agent)}
          </span>
        )}
      </div>
    </div>
  );
}

function ToolDoneIcon({ kind }: { kind: "search" | "chart" | "agent" }) {
  if (kind === "search") {
    return (
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.5"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
      </svg>
    );
  }
  if (kind === "agent") {
    // Right-facing arrow inside a circle — signals "handoff/route to".
    return (
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.5"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M9 12h6" />
        <path d="m13 9 3 3-3 3" />
      </svg>
    );
  }
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2.5"
    >
      <path d="M3 3v18h18" />
      <path d="m7 16 4-4 3 3 5-7" />
    </svg>
  );
}

function ReasoningBlock({
  text,
  streaming,
  agent,
  showThinking,
}: {
  text: string;
  streaming: boolean;
  agent?: string;
  showThinking: boolean;
}) {
  // With "show thinking" on, the block auto-expands while the model streams its
  // reasoning, then collapses when done (the original behaviour). With it off,
  // it stays collapsed until the user opens it. React only writes the `open`
  // attribute when this value changes between renders, so a manual toggle in
  // the off state (value stays `false`) is preserved.
  return (
    <details
      open={showThinking && streaming}
      className="rounded-lg border border-border/60 bg-muted/30 text-xs text-muted-foreground"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-1.5 select-none">
        {streaming ? <Spinner /> : <ThinkingIcon />}
        <span className="font-medium">{streaming ? "Thinking..." : "Thought process"}</span>
        {agent && (
          <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground/70">
            {agentLabel(agent)}
          </span>
        )}
      </summary>
      <div className="border-t border-border/60 px-3 py-2 whitespace-pre-wrap leading-relaxed">
        {text}
      </div>
    </details>
  );
}

function Dots() {
  return (
    <div className="inline-flex rounded-2xl rounded-bl-md border border-border/60 bg-card/50 px-4 py-3 backdrop-blur-sm">
      <div className="flex gap-1">
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.3s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.15s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60" />
      </div>
    </div>
  );
}

function ThinkingIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
    >
      <path d="M9 18h6" />
      <path d="M10 22h4" />
      <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8a6 6 0 0 0-12 0c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
    </svg>
  );
}

function ThinkingBubble() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl rounded-bl-md border border-border/60 bg-card/50 px-4 py-3 backdrop-blur-sm">
        <div className="flex gap-1">
          <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.3s]" />
          <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.15s]" />
          <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60" />
        </div>
      </div>
    </div>
  );
}

function ErrorBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] rounded-2xl rounded-bl-md border border-destructive/30 bg-destructive/10 px-4 py-2.5 text-sm text-destructive">
        {text}
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" className="animate-spin">
      <circle
        cx="12"
        cy="12"
        fill="none"
        r="10"
        stroke="currentColor"
        strokeOpacity="0.3"
        strokeWidth="3"
      />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="3"
      />
    </svg>
  );
}
