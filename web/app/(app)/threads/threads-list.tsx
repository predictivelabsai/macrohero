"use client";

import Link from "next/link";
import { useTransition } from "react";

import { cn } from "@/lib/utils";
import type { ChatSessionSummary } from "@/lib/chat";

import { deleteSessionAction } from "../chat/actions";

export function ThreadsList({ sessions }: { sessions: ChatSessionSummary[] }) {
  if (sessions.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border px-6 py-16 text-center">
        <p className="text-sm text-muted-foreground">No threads yet.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Start a chat to see it here.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
      {sessions.map((s) => (
        <ThreadRow key={s.id} session={s} />
      ))}
    </ul>
  );
}

function ThreadRow({ session }: { session: ChatSessionSummary }) {
  const [isDeleting, startDelete] = useTransition();

  return (
    <li className="group/row relative">
      <Link
        href={`/chat/${session.id}`}
        className="block px-4 py-3 pr-12 transition-colors hover:bg-muted"
      >
        <div className="truncate text-sm font-medium text-foreground">
          {session.title || "New chat"}
        </div>
        <div className="mt-0.5 text-xs text-muted-foreground">
          {formatTime(session.updated_at)}
        </div>
      </Link>
      <button
        type="button"
        aria-label="Delete thread"
        disabled={isDeleting}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (!confirm(`Delete "${session.title || "New chat"}"?`)) return;
          startDelete(() => deleteSessionAction(session.id, false));
        }}
        className={cn(
          "absolute top-1/2 right-3 -translate-y-1/2 rounded p-1.5 text-muted-foreground",
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
          aria-hidden="true"
        >
          <path d="M3 6h18" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
          <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    </li>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const now = Date.now();
  const diffSec = Math.round((now - d.getTime()) / 1000);
  if (diffSec < 60) return "just now";
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric",
  });
}
