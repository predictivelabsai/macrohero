import { notFound } from "next/navigation";

import { getSession } from "@/lib/chat";

import { ChatUI, type InitialMessage } from "../chat-ui";

export default async function ChatSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const session = await getSession(sessionId);
  if (!session) notFound();

  const initialMessages: InitialMessage[] = session.messages.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    reasoning: m.reasoning ?? "",
    actions: m.actions,
    parts: m.parts ?? [],
  }));

  return <ChatUI sessionId={sessionId} initialMessages={initialMessages} />;
}
