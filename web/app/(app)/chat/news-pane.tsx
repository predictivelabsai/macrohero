"use client";

import { useEffect, useState } from "react";

import type { NewsItem } from "@/lib/news";

type State =
  | { kind: "loading" }
  | { kind: "ready"; items: NewsItem[] }
  | { kind: "error"; message: string };

export function NewsPane() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/news", { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { items: NewsItem[] };
        if (!cancelled) setState({ kind: "ready", items: data.items });
      } catch (err) {
        if (!cancelled) {
          setState({
            kind: "error",
            message: err instanceof Error ? err.message : "Failed to load",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-l border-border bg-sidebar/40">
      <div className="border-b border-border px-4 py-3">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold tracking-tight">
          <LiveNewsIcon />
          Live news
        </h2>
        <p className="text-xs text-muted-foreground">Fed · ECB · BoE · FT</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        {state.kind === "loading" && <LoadingState />}
        {state.kind === "error" && <ErrorState message={state.message} />}
        {state.kind === "ready" && <ItemList items={state.items} />}
      </div>
    </aside>
  );
}

function ItemList({ items }: { items: NewsItem[] }) {
  if (items.length === 0) {
    return <p className="px-4 py-6 text-xs text-muted-foreground">No items.</p>;
  }
  return (
    <ul className="divide-y divide-border">
      {items.map((item) => (
        <li key={item.id}>
          <a
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            className="block px-4 py-3 transition-colors hover:bg-muted"
          >
            <div className="text-sm leading-snug font-medium text-foreground">{item.title}</div>
            <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span className="rounded bg-secondary px-1.5 py-0.5 text-secondary-foreground">
                {item.source}
              </span>
              {item.author && <span className="truncate">{item.author}</span>}
              <span className="ml-auto shrink-0">{formatTime(item.publishedAt)}</span>
            </div>
          </a>
        </li>
      ))}
    </ul>
  );
}

function LoadingState() {
  return (
    <ul className="divide-y divide-border">
      {Array.from({ length: 6 }).map((_, i) => (
        <li key={i} className="px-4 py-3">
          <div className="h-3.5 w-5/6 animate-pulse rounded bg-muted" />
          <div className="mt-2 h-2.5 w-1/2 animate-pulse rounded bg-muted/70" />
        </li>
      ))}
    </ul>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="px-4 py-6 text-xs text-muted-foreground">
      <p>Couldn&apos;t load news.</p>
      <p className="mt-1 text-destructive/80">{message}</p>
    </div>
  );
}

function LiveNewsIcon() {
  // Broadcast/radio-waves glyph — signals the "live" feed visually.
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      className="text-primary"
      aria-hidden="true"
    >
      <path d="M4.93 19.07A10 10 0 0 1 4.93 4.93" />
      <path d="M7.76 16.24a6 6 0 0 1 0-8.48" />
      <path d="M16.24 7.76a6 6 0 0 1 0 8.48" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </svg>
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
