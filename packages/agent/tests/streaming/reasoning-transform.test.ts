import { describe, expect, it, vi } from "vitest";
import { transformLangGraphEvents, type StreamWriter } from "../../src/streaming/reasoning-transform.js";

interface FakeChunk {
  additional_kwargs?: { reasoning_content?: string };
  content?: string;
}

interface FakeEvent {
  event: string;
  name?: string;
  data?: {
    chunk?: FakeChunk;
    output?: unknown;
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
    // The same reasoning id should be reused across the deltas.
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

  it("ignores tool_end for other tools", async () => {
    const { writer, writes } = makeWriter();
    const events: FakeEvent[] = [
      { event: "on_tool_end", name: "search_current_events", data: { output: {} } },
    ];

    await drain(transformLangGraphEvents(asAsyncIter(events), writer));

    expect(writes).toEqual([]);
  });
});
