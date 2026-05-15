"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#team", label: "Team" },
];

export function MarketingMobileNav() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-md text-foreground/80 transition-colors hover:bg-muted hover:text-foreground md:hidden"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          {open ? (
            <>
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </>
          ) : (
            <>
              <path d="M3 6h18" />
              <path d="M3 12h18" />
              <path d="M3 18h18" />
            </>
          )}
        </svg>
      </button>

      {open && (
        <div
          onClick={() => setOpen(false)}
          className="fixed inset-x-0 top-14 bottom-0 z-30 bg-background/80 backdrop-blur-sm md:hidden"
          aria-hidden="true"
        />
      )}
      <div
        className={cn(
          "fixed inset-x-0 top-14 z-40 origin-top border-b border-border/40 bg-background/95 shadow-lg backdrop-blur transition-all duration-200 md:hidden",
          open ? "translate-y-0 opacity-100" : "pointer-events-none -translate-y-2 opacity-0",
        )}
        aria-hidden={!open}
      >
        <nav className="flex flex-col px-6 py-4">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="border-b border-border/30 py-3 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground transition-colors last:border-b-0 hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
          <div className="mt-4 flex flex-col gap-2">
            <Link
              href="/sign-in"
              onClick={() => setOpen(false)}
              className="rounded-md border border-border bg-secondary px-4 py-2 text-center text-sm transition-colors hover:bg-secondary/80"
            >
              Sign in
            </Link>
            <Link
              href="/sign-up"
              onClick={() => setOpen(false)}
              className="rounded-md bg-primary px-4 py-2 text-center text-sm text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Get started
            </Link>
          </div>
        </nav>
      </div>
    </>
  );
}
