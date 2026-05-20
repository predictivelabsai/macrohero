"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function ShowThinkingCard({ current }: { current: boolean }) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(current);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = async () => {
    if (saving) return;
    const next = !enabled;
    setEnabled(next);
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/me", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ show_thinking: next }),
      });
      if (!r.ok) throw new Error(`Save failed (${r.status})`);
      router.refresh();
    } catch (e) {
      setEnabled(!next);
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="gap-3 rounded-2xl border border-border/40 bg-card/40 py-4 ring-0 backdrop-blur-xl">
      <CardHeader>
        <CardTitle className="text-base">Show thinking</CardTitle>
        <CardDescription>
          When on, the agent&apos;s full thought process and the messages it exchanges with
          sub-agents stream into the chat as they happen. When off, the thought process stays
          collapsed until you open it, and sub-agent messages are hidden behind a compact
          &ldquo;communicating with&rdquo; line.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            {enabled ? "On" : "Off"}
          </span>
          <Switch checked={enabled} onToggle={toggle} disabled={saving} />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}

function Switch({
  checked,
  onToggle,
  disabled,
}: {
  checked: boolean;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label="Show thinking"
      onClick={onToggle}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors outline-none focus-visible:shadow-[0_0_0_3px_oklch(0.72_0.2_235/0.12)] disabled:cursor-not-allowed disabled:opacity-60",
        checked ? "border-primary/50 bg-primary/80" : "border-border/70 bg-muted/60",
      )}
    >
      <span
        className={cn(
          "inline-block size-4 transform rounded-full bg-background shadow-sm transition-transform",
          checked ? "translate-x-[22px]" : "translate-x-[3px]",
        )}
      />
    </button>
  );
}
