"use client";

import { usePathname } from "next/navigation";

import { useAppChrome } from "./app-chrome";

export function MobileSidebarTrigger() {
  const { toggleSidebar, sidebarOpen } = useAppChrome();
  return (
    <button
      type="button"
      onClick={toggleSidebar}
      aria-label={sidebarOpen ? "Close menu" : "Open menu"}
      aria-expanded={sidebarOpen}
      className="-ml-1 flex h-9 w-9 items-center justify-center rounded-md text-foreground/80 transition-colors hover:bg-muted hover:text-foreground md:hidden"
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
        <path d="M3 6h18" />
        <path d="M3 12h18" />
        <path d="M3 18h18" />
      </svg>
    </button>
  );
}

export function MobileNewsTrigger() {
  const { toggleNews, newsOpen } = useAppChrome();
  const pathname = usePathname();
  // News pane is chat-specific; only surface the trigger on chat routes.
  if (!pathname.startsWith("/chat")) return null;
  return (
    <button
      type="button"
      onClick={toggleNews}
      aria-label={newsOpen ? "Close live news" : "Open live news"}
      aria-expanded={newsOpen}
      className="flex h-9 w-9 items-center justify-center rounded-md text-foreground/80 transition-colors hover:bg-muted hover:text-foreground md:hidden"
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-primary"
        aria-hidden="true"
      >
        <path d="M4.93 19.07A10 10 0 0 1 4.93 4.93" />
        <path d="M7.76 16.24a6 6 0 0 1 0-8.48" />
        <path d="M16.24 7.76a6 6 0 0 1 0 8.48" />
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
        <circle cx="12" cy="12" r="1.5" fill="currentColor" />
      </svg>
    </button>
  );
}
