import { beforeEach, describe, expect, it, vi } from "vitest";

// Spy on the ChatDeepSeek constructor so we can assert it was called with
// expected kwargs without actually contacting DeepSeek's API.
const constructorSpy = vi.fn();
vi.mock("@langchain/deepseek", () => ({
  ChatDeepSeek: class {
    constructor(args: unknown) {
      constructorSpy(args);
    }
  },
}));

const { makeLLM, makeFlashLLM } = await import("../src/llm.js");

describe("LLM factories", () => {
  beforeEach(() => {
    constructorSpy.mockClear();
  });

  it("makeLLM uses DEEPSEEK_MODEL env (or default) and streams", () => {
    vi.stubEnv("DEEPSEEK_API_KEY", "key");
    vi.stubEnv("DEEPSEEK_MODEL", "deepseek-v4-pro");
    makeLLM();
    expect(constructorSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        apiKey: "key",
        model: "deepseek-v4-pro",
        streaming: true,
      }),
    );
  });

  it("makeLLM accepts a temperature override", () => {
    vi.stubEnv("DEEPSEEK_API_KEY", "key");
    makeLLM({ temperature: 0.1 });
    expect(constructorSpy).toHaveBeenCalledWith(
      expect.objectContaining({ temperature: 0.1 }),
    );
  });

  it("makeFlashLLM uses the flash model and disables streaming", () => {
    vi.stubEnv("DEEPSEEK_API_KEY", "key");
    vi.stubEnv("DEEPSEEK_FLASH_MODEL", "deepseek-v4-flash");
    makeFlashLLM();
    expect(constructorSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        model: "deepseek-v4-flash",
        streaming: false,
        maxTokens: 80,
      }),
    );
  });
});
