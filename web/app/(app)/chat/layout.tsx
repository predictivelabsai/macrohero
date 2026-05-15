import { NewsPane } from "./news-pane";

export const metadata = { title: "Chat · MacroHero" };

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  // The global AppSidebar (../layout.tsx) owns the left rail; the chat layout
  // only adds the news pane on the right.
  return (
    <div className="flex h-full">
      <div className="min-w-0 flex-1 overflow-hidden">{children}</div>
      <NewsPane />
    </div>
  );
}
