import { describe, expect, it } from "vitest";
import { uiPartsToJsonb, extractFinalText, extractFinalReasoning } from "../../src/chat/persist.js";

describe("uiPartsToJsonb", () => {
  it("translates text parts", () => {
    expect(uiPartsToJsonb([{ type: "text", text: "hello" }])).toEqual([
      { kind: "text", text: "hello" },
    ]);
  });

  it("translates reasoning parts", () => {
    expect(uiPartsToJsonb([{ type: "reasoning", text: "thinking..." }])).toEqual([
      { kind: "reasoning", text: "thinking..." },
    ]);
  });

  it("translates tool-* parts", () => {
    const out = uiPartsToJsonb([
      {
        type: "tool-run_factor_projection",
        state: "output-available",
        input: { pair: "EUR/USD" },
        output: { projection: {} },
        toolCallId: "call_1",
      },
    ]);
    expect(out).toEqual([
      {
        kind: "tool",
        tool_name: "run_factor_projection",
        state: "output-available",
        input: { pair: "EUR/USD" },
      },
    ]);
  });

  it("translates data-scenario_projection parts", () => {
    const data = { pair: "EUR/USD", projection: { point_pct: 1.5 } };
    expect(uiPartsToJsonb([{ type: "data-scenario_projection", data }])).toEqual([
      { kind: "scenario_projection", data },
    ]);
  });

  it("drops transient data-* parts (data-session, data-session-update)", () => {
    expect(
      uiPartsToJsonb([
        { type: "data-session", data: { sessionId: "x", title: "y" } },
        { type: "data-session-update", data: { sessionId: "x", title: "z" } },
        { type: "text", text: "kept" },
      ]),
    ).toEqual([{ kind: "text", text: "kept" }]);
  });

  it("preserves order", () => {
    const out = uiPartsToJsonb([
      { type: "reasoning", text: "think" },
      { type: "text", text: "first" },
      {
        type: "tool-run_factor_projection",
        state: "output-available",
        input: {},
        toolCallId: "c",
      },
      { type: "data-scenario_projection", data: {} },
      { type: "text", text: "second" },
    ]);
    expect(out.map((p: any) => p.kind)).toEqual([
      "reasoning",
      "text",
      "tool",
      "scenario_projection",
      "text",
    ]);
  });

  it("ignores unknown part types defensively", () => {
    expect(uiPartsToJsonb([{ type: "step-start" } as any, { type: "text", text: "ok" }])).toEqual([
      { kind: "text", text: "ok" },
    ]);
  });
});

describe("extractFinalText", () => {
  it("joins all text parts", () => {
    expect(
      extractFinalText([
        { type: "text", text: "Hello" },
        { type: "reasoning", text: "..." },
        { type: "text", text: " world" },
      ]),
    ).toBe("Hello world");
  });
});

describe("extractFinalReasoning", () => {
  it("joins all reasoning parts with double newlines", () => {
    expect(
      extractFinalReasoning([
        { type: "reasoning", text: "first block" },
        { type: "text", text: "..." },
        { type: "reasoning", text: "second block" },
      ]),
    ).toBe("first block\n\nsecond block");
  });
});
