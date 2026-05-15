import Link from "next/link";
import { UserButton } from "@clerk/nextjs";

import { TimezoneDetector } from "@/components/timezone-detector";
import { listSessions } from "@/lib/chat";
import { getMe } from "@/lib/me";

import { AppChromeProvider } from "./app-chrome";
import { AppSidebar } from "./app-sidebar";
import { MobileNewsTrigger, MobileSidebarTrigger } from "./header-triggers";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const [me, sessions] = await Promise.all([getMe(), listSessions()]);
  return (
    // h-screen + overflow-hidden locks the app shell to the viewport so the
    // browser never adds a body scrollbar. Each inner panel (sidebar, chat,
    // news) owns its own overflow. Routes that need page-level scrolling
    // (e.g. /settings) wrap themselves in overflow-y-auto.
    <AppChromeProvider>
      <div className="flex h-screen flex-col overflow-hidden">
        <TimezoneDetector currentTimezone={me.timezone} />
        <header className="z-40 shrink-0 border-b border-border bg-background/80 backdrop-blur">
          <div className="flex h-14 w-full items-center justify-between gap-2 px-4 sm:px-6">
            <div className="flex min-w-0 items-center gap-1">
              <MobileSidebarTrigger />
              <Link
                href="/chat"
                className="flex items-center gap-2 font-mono text-sm font-semibold tracking-tight"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className="h-5 w-5">
                  <rect width="32" height="32" rx="6" fill="#0f172a" />
                  <polyline points="8 22 14 14 18 18 24 10" fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <polyline points="20 10 24 10 24 14" fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                MacroHero
              </Link>
            </div>
            <div className="flex items-center gap-1">
              <MobileNewsTrigger />
              <UserButton />
            </div>
          </div>
        </header>
        <div className="flex min-h-0 w-full flex-1 overflow-hidden">
          <AppSidebar sessions={sessions} />
          <main className="min-w-0 flex-1 overflow-hidden">{children}</main>
        </div>
      </div>
    </AppChromeProvider>
  );
}
