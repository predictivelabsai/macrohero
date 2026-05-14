"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";

const FALLBACK_TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Australia/Sydney",
];

function allTimezones(): string[] {
  type IntlMaybe = typeof Intl & { supportedValuesOf?: (key: string) => string[] };
  const intl = Intl as IntlMaybe;
  try {
    return intl.supportedValuesOf?.("timeZone") ?? FALLBACK_TIMEZONES;
  } catch {
    return FALLBACK_TIMEZONES;
  }
}

export function TimezoneCard({ currentTimezone }: { currentTimezone: string | null }) {
  const detected = useMemo(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    } catch {
      return "UTC";
    }
  }, []);
  const initialValue = currentTimezone ?? detected;

  return (
    <TimezoneForm
      key={initialValue}
      currentTimezone={currentTimezone}
      initialValue={initialValue}
    />
  );
}

function TimezoneForm({
  currentTimezone,
  initialValue,
}: {
  currentTimezone: string | null;
  initialValue: string;
}) {
  const router = useRouter();
  const [value, setValue] = useState<string>(initialValue);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const timezones = useMemo(() => allTimezones(), []);
  const dirty = value !== (currentTimezone ?? "");

  const save = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const r = await fetch("/api/me", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ timezone: value }),
      });
      if (!r.ok) throw new Error(`Save failed (${r.status})`);
      setSaved(true);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="gap-3 rounded-2xl border border-border/40 bg-card/40 py-4 ring-0 backdrop-blur-xl">
      <CardHeader>
        <CardTitle className="text-base">Time zone</CardTitle>
        <CardDescription>Used to display all timestamps in the app.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label
            htmlFor="timezone"
            className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground"
          >
            Timezone
          </Label>
          {/* Same mini-composer treatment as the display-name input. */}
          <select
            id="timezone"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setSaved(false);
            }}
            className="h-11 w-full rounded-2xl border border-border/70 bg-card/60 px-3.5 text-sm backdrop-blur-xl transition-all outline-none focus-visible:border-primary/50 focus-visible:bg-card/80 focus-visible:shadow-[0_0_0_3px_oklch(0.72_0.2_235/0.12)]"
          >
            {timezones.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {saved && !error && (
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-400">Saved.</p>
        )}
        <Button
          type="button"
          onClick={save}
          disabled={saving || !dirty}
          size="sm"
          className="h-8 px-3 font-mono text-xs tracking-wider uppercase"
        >
          {saving ? "Saving…" : "Save"}
        </Button>
      </CardContent>
    </Card>
  );
}
