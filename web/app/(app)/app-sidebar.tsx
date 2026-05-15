"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { cn } from "@/lib/utils";
import type { ChatSessionSummary } from "@/lib/chat";

import { deleteSessionAction } from "./chat/actions";

export function AppSidebar({ sessions }: { sessions: ChatSessionSummary[] }) {
  const pathname = usePathname();
  const router = useRouter();
  const currentSessionId = pathname.startsWith("/chat/") ? pathname.split("/")[2] : null;
  const onChatHome = pathname === "/chat";
  const onSettings = pathname.startsWith("/settings");

  // Expanded by default so chat history is discoverable; user can collapse.
  const [chatsExpanded, setChatsExpanded] = useState(true);

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-sidebar/40">
      <div className="flex flex-col gap-0.5 px-2 pt-3">
        <NavLink icon={<HomeIcon />} label="Home" href="/chat" active={onChatHome} />
        <ChatsRow
          expanded={chatsExpanded}
          onToggle={() => setChatsExpanded((v) => !v)}
          onCreate={() => router.push("/chat")}
          isOnNew={onChatHome}
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2">
        {chatsExpanded && (
          <div className="ml-3 border-l border-border pl-2">
            {sessions.length === 0 ? (
              <p className="px-2 py-1.5 text-xs text-muted-foreground">No chats yet.</p>
            ) : (
              <ul className="space-y-0.5 py-1">
                {sessions.map((s) => (
                  <SessionRow key={s.id} session={s} isCurrent={s.id === currentSessionId} />
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
      <div className="flex flex-col gap-0.5 border-t border-border px-2 py-2">
        <NavLink icon={<SettingsIcon />} label="Settings" href="/settings" active={onSettings} />
      </div>
    </aside>
  );
}

function NavLink({
  icon,
  label,
  href,
  active,
}: {
  icon: React.ReactNode;
  label: string;
  href: string;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
        active
          ? "bg-secondary text-foreground"
          : "text-foreground/80 hover:bg-muted hover:text-foreground",
      )}
    >
      <span className="text-muted-foreground">{icon}</span>
      <span>{label}</span>
    </Link>
  );
}

function ChatsRow({
  expanded,
  onToggle,
  onCreate,
  isOnNew,
}: {
  expanded: boolean;
  onToggle: () => void;
  onCreate: () => void;
  isOnNew: boolean;
}) {
  return (
    <div className="flex items-center gap-0.5">
      <button
        type="button"
        onClick={onCreate}
        title="New chat"
        className={cn(
          "flex flex-1 items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors",
          isOnNew
            ? "bg-secondary text-foreground"
            : "text-foreground/80 hover:bg-muted hover:text-foreground",
        )}
      >
        <span className="text-muted-foreground">
          <ChatsIcon />
        </span>
        <span>Chats</span>
      </button>
      <button
        type="button"
        onClick={onToggle}
        aria-label={expanded ? "Collapse chats" : "Expand chats"}
        aria-expanded={expanded}
        className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <ChevronIcon expanded={expanded} />
      </button>
    </div>
  );
}

function SessionRow({ session, isCurrent }: { session: ChatSessionSummary; isCurrent: boolean }) {
  const [isDeleting, startDelete] = useTransition();

  return (
    <li className="group/row relative animate-in fade-in slide-in-from-top-1 duration-300">
      <Link
        href={`/chat/${session.id}`}
        className={cn(
          "block rounded-md px-2.5 py-1.5 pr-8 text-sm transition-colors",
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
        <TrashIcon />
      </button>
    </li>
  );
}

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m3 10 9-7 9 7v10a2 2 0 0 1-2 2h-4v-7h-6v7H5a2 2 0 0 1-2-2z" />
    </svg>
  );
}

function ChatsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("transition-transform", expanded && "rotate-180")}
      aria-hidden="true"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}
