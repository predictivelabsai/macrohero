import { listSessions } from "@/lib/chat";

import { NewsPane } from "./news-pane";
import { ChatSidebar } from "./sidebar";

export const metadata = { title: "Chat · MacroHero" };

export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const sessions = await listSessions();
  // App layout (../layout.tsx) already constrains the parent <main> to the
  // remaining viewport height with overflow-hidden, so h-full is enough here.
  return (
    <div className="flex h-full">
      <ChatSidebar sessions={sessions} />
      <div className="min-w-0 flex-1 overflow-hidden">{children}</div>
      <NewsPane />
    </div>
  );
}
