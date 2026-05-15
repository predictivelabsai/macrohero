"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ProjectionResult } from "@/lib/scenarios";

const WARNING_LABELS: Record<string, string> = {
  low_r_squared:
    "Market drivers explain little of recent moves — treat the projection as indicative.",
  thin_pair: "Limited historical data — sensitivity estimates may be unstable.",
  singular_design:
    "Selected drivers move too closely together — one is redundant.",
  high_collinearity:
    "Several selected drivers move closely together — individual sensitivities may overlap.",
  extreme_shock:
    "Scenario is unusually large vs. recent history — extrapolation risk is high.",
  unstable_oos:
    "Recent driver relationships haven't held up out-of-sample — direction is more reliable than magnitude.",
  fat_tails:
    "Recent moves have included outliers — the confidence band may understate tail risk.",
};

function formatPct(v: number): string {
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function formatPrice(v: number): string {
  if (v >= 100) return v.toFixed(2);
  if (v >= 1) return v.toFixed(4);
  return v.toFixed(5);
}

function modelFitLabel(r2: number): { label: string; tone: "strong" | "moderate" | "weak" } {
  if (r2 >= 0.5) return { label: "Strong fit", tone: "strong" };
  if (r2 >= 0.2) return { label: "Moderate fit", tone: "moderate" };
  return { label: "Weak fit", tone: "weak" };
}

function formatSeverityHint(f: {
  severity?: "mild" | "moderate" | "severe" | "extreme" | "";
  direction?: "up" | "down" | "";
  sigma_multiple?: number;
}): string | null {
  if (!f.severity) return null;
  // e.g. "severe down · 2σ" — plain words; magnitude as absolute sigma multiple.
  const dir = f.direction ? ` ${f.direction}` : "";
  const mag = typeof f.sigma_multiple === "number" ? Math.abs(f.sigma_multiple) : null;
  const tail = mag !== null ? ` · ${mag}σ` : "";
  return `${f.severity}${dir}${tail}`;
}

export function ScenarioCard({ data }: { data: ProjectionResult }) {
  const { pair, horizon_days, r_squared, factors, projection, diagnostics } = data;

  if (projection === null) {
    return (
      <Card className="bg-background">
        <CardHeader>
          <CardTitle className="text-base">
            {pair} · {horizon_days}-day scenario
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {diagnostics.error?.message ?? "Projection unavailable."}
          </div>
        </CardContent>
      </Card>
    );
  }

  const point = projection.point_pct;
  const direction = point > 0.25 ? "up" : point < -0.25 ? "down" : "flat";
  const directionClass =
    direction === "up"
      ? "text-emerald-600 dark:text-emerald-400"
      : direction === "down"
        ? "text-rose-600 dark:text-rose-400"
        : "text-foreground";

  const sortedFactors = [...factors].sort(
    (a, b) => Math.abs(b.contribution_pct) - Math.abs(a.contribution_pct),
  );

  const fit = modelFitLabel(r_squared);
  const fitToneClass =
    fit.tone === "strong"
      ? "border-emerald-500/50 text-emerald-700 dark:text-emerald-400"
      : fit.tone === "moderate"
        ? "border-amber-500/50 text-amber-700 dark:text-amber-400"
        : "border-rose-500/50 text-rose-700 dark:text-rose-400";

  return (
    <Card className="bg-background">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0 pb-2">
        <CardTitle className="text-base">
          {pair} · {horizon_days}-day scenario
        </CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className={fitToneClass}>
            {fit.label}
          </Badge>
          {diagnostics.warnings.length > 0 && (
            <Badge variant="outline" className="border-amber-500 text-amber-700">
              {diagnostics.warnings.length} caveat
              {diagnostics.warnings.length > 1 ? "s" : ""}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div>
          <div className={`text-2xl font-semibold sm:text-3xl ${directionClass}`}>{formatPct(point)}</div>
          <div className="text-sm text-muted-foreground">
            {formatPrice(projection.spot_at_t0)} → {formatPrice(projection.projected_spot)}
          </div>
        </div>

        <BandBar
          point={point}
          low={projection.band_95_low_pct}
          high={projection.band_95_high_pct}
        />
        <div className="text-xs text-muted-foreground">
          Shaded range covers roughly 95% of likely outcomes; the line marks the central estimate.
        </div>

        <Separator />

        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Driver</TableHead>
                <TableHead className="text-right">Expected change</TableHead>
                <TableHead className="text-right">Sensitivity</TableHead>
                <TableHead className="text-right">Contribution</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedFactors.map((f) => {
                const contribClass =
                  f.contribution_pct > 0.01
                    ? "text-emerald-600 dark:text-emerald-400"
                    : f.contribution_pct < -0.01
                      ? "text-rose-600 dark:text-rose-400"
                      : "";
                const severityHint = formatSeverityHint(f);
                return (
                  <TableRow key={f.name}>
                    <TableCell className="font-medium">{f.name}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex flex-col items-end gap-0.5">
                        <span>
                          {f.expected_change >= 0 ? "+" : ""}
                          {f.expected_change.toFixed(f.unit === "bp" ? 0 : 1)}
                          {f.unit}
                        </span>
                        {severityHint && (
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {severityHint}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">{f.beta.toFixed(3)}</TableCell>
                    <TableCell className={`text-right ${contribClass}`}>
                      {formatPct(f.contribution_pct)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {diagnostics.warnings.length > 0 && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
            <div className="font-medium text-amber-700 dark:text-amber-400 mb-1">
              Caveats to keep in mind
            </div>
            <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
              {diagnostics.warnings.map((w) => (
                <li key={w}>{WARNING_LABELS[w] ?? w}</li>
              ))}
            </ul>
          </div>
        )}

        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none hover:text-foreground transition-colors">
            Show technical details
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 pl-2">
            <div>R² (in-sample fit)</div>
            <div className="text-right font-mono">{r_squared.toFixed(3)}</div>
            <div>Observations</div>
            <div className="text-right font-mono">{diagnostics.n_observations}</div>
            <div>Regression window</div>
            <div className="text-right font-mono">{data.regression_window_days} days</div>
            <div>Intercept</div>
            <div className="text-right font-mono">{data.intercept.toFixed(5)}</div>
          </div>
          <div className="mt-2 pl-2">
            <div className="font-medium text-foreground mb-1">Driver coefficients (β)</div>
            <ul className="space-y-0.5">
              {sortedFactors.map((f) => (
                <li key={f.name} className="flex justify-between">
                  <span>{f.name}</span>
                  <span className="font-mono">{f.beta.toFixed(4)}</span>
                </li>
              ))}
            </ul>
          </div>
        </details>
      </CardContent>
    </Card>
  );
}

function BandBar({ point, low, high }: { point: number; low: number; high: number }) {
  // Pick a domain that's slightly wider than the band so the bar has breathing
  // room. For very narrow bands we still want a meaningful visual range.
  const span = Math.max(high - low, 1.0); // at least 1%-wide visual range
  const pad = Math.max(span * 0.2, 0.5);
  const minVal = Math.min(low, point) - pad;
  const maxVal = Math.max(high, point) + pad;
  const range = maxVal - minVal;
  const pct = (v: number) => ((v - minVal) / range) * 100;

  const zeroVisible = minVal < 0 && maxVal > 0;
  const pointLeft = pct(point);
  const bandLeft = pct(low);
  const bandWidth = pct(high) - pct(low);

  return (
    <div className="space-y-1.5">
      <div className="relative h-9 rounded-md border border-border/40 bg-muted/20">
        {/* Zero reference line (rendered only when 0 is in the visible range) */}
        {zeroVisible && (
          <div
            className="absolute inset-y-0 w-px bg-border"
            style={{ left: `${pct(0)}%` }}
            aria-hidden="true"
          />
        )}
        {/* 95% band shading */}
        <div
          className="absolute inset-y-1 rounded-sm bg-primary/25"
          style={{
            left: `${bandLeft}%`,
            width: `${Math.max(bandWidth, 0.5)}%`,
          }}
        />
        {/* Central estimate line */}
        <div
          className="absolute inset-y-0 w-0.5 bg-primary"
          style={{ left: `${pointLeft}%` }}
          aria-hidden="true"
        />
      </div>
      <div className="relative flex justify-between text-[10px] font-mono text-muted-foreground">
        <span>{formatPct(minVal)}</span>
        {zeroVisible && (
          <span
            className="absolute -translate-x-1/2"
            style={{ left: `${pct(0)}%` }}
          >
            0%
          </span>
        )}
        <span>{formatPct(maxVal)}</span>
      </div>
    </div>
  );
}
