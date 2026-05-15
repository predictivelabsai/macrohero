import Link from "next/link";

import { AnimatedBackground } from "./animated-background";
import { MarketingMobileNav } from "./marketing-mobile-nav";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <AnimatedBackground />
      <header className="sticky top-0 z-20 border-b border-border/40 bg-background/50 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/chat" className="flex items-center gap-2 font-mono text-sm font-semibold tracking-tight">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" className="h-5 w-5">
              <rect width="32" height="32" rx="6" fill="#0f172a" />
              <polyline points="8 22 14 14 18 18 24 10" fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <polyline points="20 10 24 10 24 14" fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            MacroHero
          </Link>
          <nav className="hidden items-center gap-7 md:flex">
            <a
              href="#features"
              className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground"
            >
              How it works
            </a>
            <a
              href="#team"
              className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground"
            >
              Team
            </a>
          </nav>
          <MarketingMobileNav />
        </div>
      </header>
      <main className="relative z-10 flex-1">{children}</main>
      <footer className="relative z-10 border-t border-border/40 bg-background py-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 text-sm text-muted-foreground sm:px-6">
          <span>© {new Date().getFullYear()} MacroHero</span>
        </div>
      </footer>
    </div>
  );
}
