"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ChatSessionSummary } from "@/lib/chat";

import { deleteSessionAction } from "./actions";

export function ChatSidebar({ sessions }: { sessions: ChatSessionSummary[] }) {
  const pathname = usePathname();
  const router = useRouter();
  const currentId = pathname.startsWith("/chat/") ? pathname.split("/")[2] : null;
  const onNew = pathname === "/chat";

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-sidebar/40">
      <div className="px-3 py-3">
        <Button
          size="lg"
          variant="outline"
          className="w-full justify-center"
          disabled={onNew}
          onClick={() => router.push("/chat")}
        >
          + New chat
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {sessions.length === 0 ? (
          <p className="px-2 pt-2 text-xs text-muted-foreground">No chats yet.</p>
        ) : (
          <ul className="space-y-0.5">
            {sessions.map((s) => (
              <SessionRow
                key={s.id}
                session={s}
                isCurrent={s.id === currentId}
              />
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

function SessionRow({
  session,
  isCurrent,
}: {
  session: ChatSessionSummary;
  isCurrent: boolean;
}) {
  const [isDeleting, startDelete] = useTransition();

  return (
    <li
      // Fresh rows (new key from React's POV after router.refresh) trigger
      // the slide-in once on mount; existing rows are reconciled in place
      // by their session.id key, so they don't re-animate.
      className="group/row relative animate-in fade-in slide-in-from-top-1 duration-300"
    >
      <Link
        href={`/chat/${session.id}`}
        className={cn(
          "block rounded-md px-2.5 py-2 pr-8 text-sm transition-colors",
          isCurrent
            ? "bg-secondary text-secondary-foreground"
            : "text-foreground/80 hover:bg-muted",
        )}
      >
        <div className="truncate">{session.title || "New chat"}</div>
      </Link>
      <button
        type="button"
        aria-label="Delete chat"
        disabled={isDeleting}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (!confirm(`Delete "${session.title || "New chat"}"?`)) return;
          startDelete(() => deleteSessionAction(session.id, isCurrent));
        }}
        className={cn(
          "absolute top-1/2 right-1.5 -translate-y-1/2 rounded p-1 text-muted-foreground",
          "opacity-0 transition-opacity group-hover/row:opacity-100 hover:bg-destructive/10 hover:text-destructive",
          "focus-visible:opacity-100",
        )}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M3 6h18" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
          <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    </li>
  );
}
