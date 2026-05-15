import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { listSessions } from "@/lib/chat";

import { ThreadsList } from "./threads-list";

export const metadata = { title: "Threads · MacroHero" };

export default async function ThreadsPage() {
  const sessions = await listSessions();

  return (
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Threads</h1>
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
