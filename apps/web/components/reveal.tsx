"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

type RevealProps = {
  children: React.ReactNode;
  /** Optional delay in ms before the entry animation starts. */
  delay?: number;
  /** Class applied to the wrapper. */
  className?: string;
  /** Render as a different element (defaults to div). */
  as?: "div" | "section" | "article" | "header";
};

/**
 * Reveal-on-scroll wrapper. Renders children hidden, then flips
 * data-reveal from "out" to "in" the first time the element crosses
 * ~15% of the viewport. The animation itself is defined in globals.css.
 *
 * IntersectionObserver is created once per instance, disconnected after
 * the first reveal so we don't keep observing live nodes.
 */
export function Reveal({ children, delay = 0, className, as = "div" }: RevealProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || revealed) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setRevealed(true);
            obs.disconnect();
            break;
          }
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [revealed]);

  const Tag = as;
  return (
    <Tag
      ref={ref as React.Ref<HTMLDivElement>}
      data-reveal={revealed ? "in" : "out"}
      style={delay ? { animationDelay: `${delay}ms` } : undefined}
      className={cn(className)}
    >
      {children}
    </Tag>
  );
}
