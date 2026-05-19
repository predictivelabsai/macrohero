import "server-only";

import { apiFetch } from "@/lib/api";
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
  | { kind: "tool"; tool_name: string; action_id: string | null; agent?: string }
  | { kind: "scenario_projection"; data: ProjectionResult };

export type ChatMessageRow = {
  id: string;
  ordinal: number;
  role: "user" | "assistant";
  content: string;
  reasoning: string;
  actions: ChatAction[];
  parts: ChatMessagePart[];
  created_at: string;
};

export type ChatSessionSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatSessionDetail = ChatSessionSummary & {
  messages: ChatMessageRow[];
};

export async function listSessions(): Promise<ChatSessionSummary[]> {
  try {
    return await apiFetch<ChatSessionSummary[]>("/chat/sessions");
  } catch {
    return [];
  }
}

export async function getSession(id: string): Promise<ChatSessionDetail | null> {
  try {
    return await apiFetch<ChatSessionDetail>(`/chat/sessions/${id}`);
  } catch {
    return null;
  }
}
