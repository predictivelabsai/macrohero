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
 * Mirrors api/src/macrohero/chat/title.py.
 */
export async function summarizeTitle(content: string): Promise<string | null> {
  const cleanedInput = content.split(/\s+/).filter(Boolean).join(" ");
  if (!cleanedInput) return null;

  let llm;
  try {
    llm = makeFlashLLM();
  } catch {
    // Missing DEEPSEEK_API_KEY etc. — surface as no title rather than crash.
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
  } catch {
    return null;
  }

  const raw = typeof response.content === "string" ? response.content : "";
  const title = clean(raw);
  return title.length > 0 ? title : null;
}
