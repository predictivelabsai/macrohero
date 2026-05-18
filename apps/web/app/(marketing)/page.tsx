import Link from "next/link";

import { Reveal } from "@/components/reveal";
import { buttonVariants } from "@/components/ui/button";

const features = [
  {
    icon: "📊",
    title: "Agentic Chat",
    body: "Ask questions about macro events, FX movements, and central bank decisions. The AI agent searches the web, queries the news database, and generates structured analysis with strategy recommendations.",
  },
  {
    icon: "📈",
    title: "FX Backtesting",
    body: "Backtest momentum strategies on major currency pairs with configurable parameters — lookback period, take profit, stop loss. Get Sharpe ratio, max drawdown, equity curves, and full trade logs.",
  },
  {
    icon: "⚡",
    title: "Market Movers",
    body: "Real-time identification of the highest-impact macro news stories, ranked by predicted FX magnitude and direction. Track which events are moving markets right now.",
  },
  {
    icon: "📉",
    title: "Treasury vs FX Charts",
    body: "Interactive dual-axis Plotly charts comparing US Treasury yields against FX pairs. Visualize the interest rate differential channel in real time.",
  },
  {
    icon: "📰",
    title: "Live News Feed",
    body: "Continuous RSS ingestion from Financial Times, Bloomberg, Wall Street Journal, Reuters, and CNBC. AI-enriched with sentiment, currency tags, and predicted impact.",
  },
  {
    icon: "📅",
    title: "Economic Calendar",
    body: "Upcoming macro events from EODHD — central bank meetings, employment reports, GDP releases. Filtered by impact level and country.",
  },
  {
    icon: "🤖",
    title: "Strategy Agent",
    body: "Specialized backtest strategy agent that designs optimal parameters based on macro regime classification — geopolitical shock, trending, range-bound, or high volatility.",
  },
  {
    icon: "🗂️",
    title: "Event Categories",
    body: "Seven macro event categories — Central Bank, Earnings, GDP, Trade & Tariffs, Employment, Inflation, Geopolitical — each with keyword-based auto-classification.",
  },
];

const howItWorks = [
  {
    title: "Ask a Question",
    body: "Type a macro question or select a shortcut — 'FX strategies for a Hormuz deal', 'Backtest EUR/USD momentum', 'What's moving markets today'. The AI agent takes it from there.",
  },
  {
    title: "Get Structured Analysis",
    body: "MacroHero responds with a professional trading-desk format: Macro Framework table, Strategy Breakdown with conviction levels, Summary Table, and actionable next steps tied to specific backtests.",
  },
  {
    title: "Backtest and Iterate",
    body: "Click a backtest suggestion to run it instantly. Watch trades stream in live. Compare parameter sets. Refine your strategy with real historical data before committing capital.",
  },
];

const team = [
  {
    initials: "AS",
    name: "Andrew Simon",
    linkedin: "https://www.linkedin.com/in/andrew-simon-43041728/",
  },
  {
    initials: "JK",
    name: "Julian Kaljuvee",
    linkedin: "https://www.linkedin.com/in/juliankaljuvee/",
  },
];

export default function LandingPage() {
  return (
    <>
      <section className="relative mx-auto max-w-6xl px-4 pt-16 pb-16 text-center sm:px-6 sm:pt-24 sm:pb-20 lg:pt-32">
        <span
          className="animate-fade-in font-mono text-[11px] uppercase tracking-[0.22em] text-primary"
          style={{ animationDelay: "60ms" }}
        >
          AI-powered macro intelligence
        </span>
        <h1
          className="mt-5 animate-fade-up font-heading text-5xl font-semibold leading-[1.05] tracking-tight sm:text-7xl"
          style={{ animationDelay: "180ms" }}
        >
          Macro intelligence for{" "}
          <span className="text-primary">FX and rates</span> trading.
        </h1>
        <p
          className="mx-auto mt-6 animate-fade-up text-lg text-muted-foreground sm:text-xl"
          style={{ animationDelay: "340ms" }}
        >
          MacroHero combines real-time macro news analysis, AI-driven FX strategy generation, and
          institutional-grade backtesting — giving traders and analysts the edge in an increasingly
          complex global macro landscape.
        </p>
        <p
          className="mx-auto mt-3 animate-fade-up text-sm text-muted-foreground/80"
          style={{ animationDelay: "460ms" }}
        >
          Built by macro strategists and quant developers, inspired by{" "}
          <a
            href="https://macrohive.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline-offset-4 transition-colors hover:underline hover:text-primary/80"
          >
            Macro Hive
          </a>
          .
        </p>
        <div
          className="mt-10 flex animate-fade-up items-center justify-center gap-3"
          style={{ animationDelay: "560ms" }}
        >
          <Link href="/sign-up" className={buttonVariants({ size: "lg" })}>
            Get started
          </Link>
          <Link href="/sign-in" className={buttonVariants({ variant: "secondary", size: "lg" })}>
            Sign in
          </Link>
        </div>
      </section>

      <Reveal as="section" className="mx-auto max-w-4xl px-4 pb-20 sm:px-6">
        <div className="rounded-2xl border border-border bg-background/60 p-8 text-center backdrop-blur sm:p-10">
          <p className="text-lg leading-relaxed text-muted-foreground sm:text-xl">
            MacroHero is the workspace macro strategists, FX traders, and portfolio managers use to
            track global events, generate trade ideas, and backtest strategies — all powered by AI
            and real-time data.
          </p>
        </div>
      </Reveal>

      <Reveal as="section" className="mx-auto max-w-6xl px-4 sm:px-6 pb-24">
        <div id="features" className="mb-12">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
            Features
          </span>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-5xl">
            Eight tools, <span className="text-primary">one</span> macro intelligence platform.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
            Everything a macro desk needs — research, strategy, backtesting, and live data — in one
            workspace.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <Reveal key={f.title} as="article" delay={i * 60}>
              <div className="group relative rounded-2xl border border-border bg-background/70 p-7 backdrop-blur transition-all hover:border-primary/60 hover:bg-background/90">
                <div className="mb-5 flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-lg ring-1 ring-primary/20 transition-shadow group-hover:ring-primary/40">
                    {f.icon}
                  </div>
                  <span className="font-mono text-xs tracking-[0.22em] text-muted-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="mb-2 font-heading text-xl font-semibold tracking-tight">{f.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{f.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Reveal>

      <Reveal as="section" className="mx-auto max-w-6xl px-4 sm:px-6 pb-24">
        <div id="how-it-works" className="mb-12">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
            How it works
          </span>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-5xl">
            From question to <span className="text-primary">actionable</span> strategy in three
            steps.
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {howItWorks.map((s, i) => (
            <Reveal key={s.title} as="article" delay={i * 100}>
              <div className="relative rounded-2xl border border-border bg-background/70 p-7 backdrop-blur transition-colors hover:border-primary/60">
                <span className="font-mono text-xs tracking-[0.22em] text-muted-foreground">
                  Step {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="mt-3 mb-2 font-heading text-xl font-semibold tracking-tight">{s.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Reveal>

      <Reveal as="section" className="mx-auto max-w-6xl px-4 sm:px-6 pb-32">
        <div id="team" className="mb-12">
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
            Team
          </span>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight sm:text-5xl">
            Built by macro strategists and quant developers.
          </h2>
        </div>
        <div className="grid max-w-md grid-cols-2 gap-6">
          {team.map((m) => (
            <article key={m.name}>
              <div className="flex aspect-square w-full items-center justify-center rounded-xl border border-border bg-secondary">
                <span className="text-2xl font-medium text-primary">{m.initials}</span>
              </div>
              <div className="mt-4 flex items-center gap-2 px-1">
                <h4 className="text-base font-medium">{m.name}</h4>
                <a
                  href={m.linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`${m.name} on LinkedIn`}
                  className="text-muted-foreground transition-colors hover:text-primary"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                </a>
              </div>
            </article>
          ))}
        </div>
      </Reveal>
    </>
  );
}
