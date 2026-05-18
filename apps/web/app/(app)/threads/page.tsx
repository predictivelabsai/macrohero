import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { listSessions } from "@/lib/chat";

import { ThreadsList } from "./threads-list";

export const metadata = { title: "Threads · MacroHero" };

export default async function ThreadsPage() {
  const sessions = await listSessions();

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
      {/* No max-width: the list fills whatever the chat-shell hands us. Each
          row's title relies on CSS `truncate` to ellipse only when the row is
          actually too narrow — long titles render in full whenever they fit. */}
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Threads</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              All your conversations.
            </p>
          </div>
          <Link href="/chat" className={buttonVariants({ variant: "default", size: "lg" })}>
            New chat +
          </Link>
        </div>
        <ThreadsList sessions={sessions} />
      </div>
    </div>
  );
}
