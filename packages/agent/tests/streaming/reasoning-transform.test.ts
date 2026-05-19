import { describe, expect, it } from "vitest";
import { transformLangGraphEvents, type StreamWriter } from "../../src/streaming/reasoning-transform.js";

interface FakeChunk {
  additional_kwargs?: { reasoning_content?: string };
  content?: string;
  tool_call_chunks?: Array<{
    name?: string;
    args?: string;
    id?: string;
    index?: number;
  }>;
}

interface FakeEvent {
  event: string;
  name?: string;
  run_id?: string;
  metadata?: Record<string, unknown>;
  data?: {
    chunk?: FakeChunk;
    output?: unknown;
    input?: unknown;
  };
}

async function* asAsyncIter<T>(items: T[]): AsyncIterable<T> {
  for (const item of items) yield item;
}

function makeWriter(): { writer: StreamWriter; writes: Array<Record<string, unknown>> } {
  const writes: Array<Record<string, unknown>> = [];
  const writer: StreamWriter = {
    write: (data) => {
      writes.push(data as Record<string, unknown>);
    },
  };
  return { writer, writes };
}

async function drain<T>(it: AsyncIterable<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const v of it) out.push(v);
  return out;
}

describe("transformLangGraphEvents", () => {
  it("passes through all events unchanged", async () => {
    const { writer } = makeWriter();
    const events: FakeEvent[] = [
      { event: "on_chain_start" },
      { event: "on_chat_model_stream", data: { chunk: { content: "hello" } } },
      { event: "on_chain_end" },
    ];

    const out = await drain(transformLangGraphEvents(asAsyncIter(events), writer));
    expect(out).toEqual(events);
  });

  it("emits reasoning-start/delta/end when reasoning_content appears", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      {
        event: "on_chat_model_stream",
        data: { chunk: { additional_kwargs: { reasoning_content: "think a" } } },
      },
      {
        event: "on_chat_model_stream",
        data: { chunk: { additional_kwargs: { reasoning_content: "think b" } } },
      },
      { event: "on_chain_end" },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    expect(writes).toEqual([
      { type: "reasoning-start", id: expect.any(String) },
      { type: "reasoning-delta", id: expect.any(String), delta: "think a" },
      { type: "reasoning-delta", id: expect.any(String), delta: "think b" },
      { type: "reasoning-end", id: expect.any(String) },
    ]);
    const ids = (writes as Array<{ id: string }>).map((w) => w.id);
    expect(new Set(ids).size).toBe(1);
  });

  it("emits data-scenario_projection on run_factor_projection tool_end", async () => {
    const { writer, writes } = makeWriter();
    const projectionOutput = {
      pair: "EUR/USD",
      projection: { point_pct: 1.5 },
      diagnostics: { error: null, warnings: [] },
      factors: [],
    };
    const events: FakeEvent[] = [
      {
        event: "on_tool_end",
        name: "run_factor_projection",
        data: { output: projectionOutput },
      },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    expect(writes).toEqual([
      {
        type: "data-scenario_projection",
        id: expect.any(String),
        data: projectionOutput,
        transient: false,
      },
    ]);
  });

  it("ignores tool_end for tools without run_id", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      { event: "on_tool_end", name: "search_current_events", data: { output: {} } },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    expect(writes).toEqual([]);
  });

  it("attaches agent name via providerMetadata when langgraph_node is the agent directly", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      { event: "on_chat_model_start", metadata: { langgraph_node: "research" } },
      {
        event: "on_chat_model_stream",
        metadata: { langgraph_node: "research" },
        data: { chunk: { content: "the finding" } },
      },
      { event: "on_chat_model_end", metadata: { langgraph_node: "research" } },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    const textStart = writes.find((w) => w.type === "text-start");
    expect(textStart).toMatchObject({
      type: "text-start",
      providerMetadata: { macrohero: { agent: "research" } },
    });
  });

  it("derives agent name from langgraph_checkpoint_ns when langgraph_node is the inner node", async () => {
    const { writer, writes } = makeWriter();
    // Real-world shape: react-agent's inner "agent" node fires the LLM, but
    // the outer subgraph is named after the supervisor pattern's agent.
    const events: FakeEvent[] = [
      {
        event: "on_chat_model_start",
        metadata: { langgraph_node: "agent", langgraph_checkpoint_ns: "research:abc123" },
      },
      {
        event: "on_chat_model_stream",
        metadata: { langgraph_node: "agent", langgraph_checkpoint_ns: "research:abc123" },
        data: { chunk: { additional_kwargs: { reasoning_content: "thinking" } } },
      },
      {
        event: "on_chat_model_end",
        metadata: { langgraph_node: "agent", langgraph_checkpoint_ns: "research:abc123" },
      },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    const reasoningStart = writes.find((w) => w.type === "reasoning-start");
    expect(reasoningStart).toMatchObject({
      type: "reasoning-start",
      providerMetadata: { macrohero: { agent: "research" } },
    });
  });

  it("derives agent name from langgraph_checkpoint_ns for tool runs (langgraph_node='tools')", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      {
        event: "on_tool_start",
        name: "search_current_events",
        run_id: "run_123",
        metadata: { langgraph_node: "tools", langgraph_checkpoint_ns: "research:abc|tools:def" },
        data: { input: { query: "Hormuz" } },
      },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    expect(writes).toEqual([
      {
        type: "tool-input-available",
        toolCallId: "run_123",
        toolName: "search_current_events",
        input: { query: "Hormuz" },
        providerMetadata: { macrohero: { agent: "research" } },
      },
    ]);
  });

  it("strips <name>X</name><content>...</content> wrappers from streamed text", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      {
        event: "on_chat_model_stream",
        data: { chunk: { content: "<name>supervisor</name><content>hello world</content>" } },
      },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    const deltas = writes.filter((w) => w.type === "text-delta");
    expect(deltas).toHaveLength(1);
    expect(deltas[0]).toMatchObject({ type: "text-delta", delta: "hello world" });
  });

  it("emits tool-input-start on the first tool_call_chunk with a name + id", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      {
        event: "on_chat_model_stream",
        metadata: { langgraph_checkpoint_ns: "supervisor:abc" },
        data: {
          chunk: {
            tool_call_chunks: [
              { name: "transfer_to_research", id: "call_42", args: "", index: 0 },
            ],
          },
        },
      },
      // subsequent chunks are arg deltas — must NOT re-fire tool-input-start
      {
        event: "on_chat_model_stream",
        metadata: { langgraph_checkpoint_ns: "supervisor:abc" },
        data: { chunk: { tool_call_chunks: [{ args: "{}", index: 0 }] } },
      },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    const starts = writes.filter((w) => w.type === "tool-input-start");
    expect(starts).toHaveLength(1);
    expect(starts[0]).toEqual({
      type: "tool-input-start",
      toolCallId: "call_42",
      toolName: "transfer_to_research",
      providerMetadata: { macrohero: { agent: "supervisor" } },
    });
  });

  it("uses the LLM's tool_call_id (not run_id) for tool-input-available when buffered", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      {
        event: "on_chat_model_stream",
        metadata: { langgraph_checkpoint_ns: "supervisor:abc" },
        data: {
          chunk: {
            tool_call_chunks: [
              { name: "transfer_to_research", id: "call_42", index: 0 },
            ],
          },
        },
      },
      {
        event: "on_chat_model_end",
        metadata: { langgraph_checkpoint_ns: "supervisor:abc" },
        data: {
          output: {
            tool_calls: [
              { id: "call_42", name: "transfer_to_research", args: {} },
            ],
          },
        },
      },
      {
        event: "on_tool_start",
        name: "transfer_to_research",
        run_id: "lg_run_xyz",
        metadata: { langgraph_checkpoint_ns: "supervisor:abc" },
        data: { input: {} },
      },
      {
        event: "on_tool_end",
        name: "transfer_to_research",
        run_id: "lg_run_xyz",
        data: { output: "Successfully transferred to research" },
      },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    const available = writes.find((w) => w.type === "tool-input-available");
    expect(available).toMatchObject({
      type: "tool-input-available",
      toolCallId: "call_42",
      toolName: "transfer_to_research",
    });

    const done = writes.find((w) => w.type === "tool-output-available");
    expect(done).toMatchObject({
      type: "tool-output-available",
      toolCallId: "call_42",
    });
  });

  it("falls back to run_id when no tool_call was buffered (e.g., synthetic tests)", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      {
        event: "on_tool_start",
        name: "search_current_events",
        run_id: "lg_run_xyz",
        metadata: { langgraph_checkpoint_ns: "research:abc|tools:def" },
        data: { input: { query: "q" } },
      },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    expect(writes).toEqual([
      {
        type: "tool-input-available",
        toolCallId: "lg_run_xyz",
        toolName: "search_current_events",
        input: { query: "q" },
        providerMetadata: { macrohero: { agent: "research" } },
      },
    ]);
  });

  it("emits text-start with no providerMetadata when no agent can be derived", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      { event: "on_chat_model_start" },
      {
        event: "on_chat_model_stream",
        data: { chunk: { content: "untagged text" } },
      },
      { event: "on_chat_model_end" },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    const textStart = writes.find((w) => w.type === "text-start");
    expect(textStart).toEqual({ type: "text-start", id: expect.any(String) });
    expect(textStart).not.toHaveProperty("providerMetadata");
  });
});
