import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { makeFlashLLM } from "./llm.js";

const TITLE_HARD_CAP = 200;

const SYSTEM_PROMPT = `You write short titles for chat sessions.

Given the user's first message, output a single descriptive title that names the topic. Rules:

- 4 to 12 words. Aim for under 80 characters; never exceed 180.
- Preserve specific entities the user mentioned (currencies, instruments, dates, events).
- Sentence case. No surrounding quotes, no trailing punctuation, no emoji.
- Output only the title text. No prefix, no explanation, no newline.`;

function clean(raw: string): string {
  let text = raw.trim().replace(/^["']|["']$/g, "").trim();
  // First line only.
  text = text.split("\n")[0] ?? "";
  // Strip trailing punctuation (matches Python's _clean: " .,:;…").
  text = text.replace(/[ .,:;…]+$/u, "");
  if (text.length > TITLE_HARD_CAP) {
    text = text.slice(0, TITLE_HARD_CAP).trimEnd();
  }
  return text;
}

/**
 * Summarize a user message into a 4-12 word session title using the flash
 * model. Returns null on any error (missing API key, timeout, empty output).
 */
export async function summarizeTitle(content: string): Promise<string | null> {
  const cleanedInput = content.split(/\s+/).filter(Boolean).join(" ");
  if (!cleanedInput) return null;

  let llm;
  try {
    llm = makeFlashLLM();
  } catch (err) {
    console.warn("[summarizeTitle] makeFlashLLM failed:", err);
    return null;
  }

  const messages = [
    new SystemMessage(SYSTEM_PROMPT),
    new HumanMessage(cleanedInput),
  ];

  let response;
  try {
    response = await Promise.race([
      llm.invoke(messages),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("title summarizer timeout")), 15_000),
      ),
    ]);
  } catch (err) {
    console.warn("[summarizeTitle] llm.invoke failed:", err);
    return null;
  }

  // ChatDeepSeek's response.content can be either a string (standard chat
  // completions) OR an array of content parts (when thinking mode emits a
  // reasoning block alongside text). Handle both.
  let raw = "";
  if (typeof response.content === "string") {
    raw = response.content;
  } else if (Array.isArray(response.content)) {
    raw = response.content
      .map((p: unknown) => {
        if (typeof p === "string") return p;
        if (p && typeof p === "object" && typeof (p as { text?: unknown }).text === "string") {
          return (p as { text: string }).text;
        }
        return "";
      })
      .join("");
  }
  // Don't use reasoning_content as a fallback — that's the model's internal
  // thinking process, not a title. If visible content is empty, return null
  // and the caller keeps the placeholder title.
  const title = clean(raw);
  return title.length > 0 ? title : null;
}
