import { tool } from "@langchain/core/tools";
import {
  runFactorProjectionArgsSchema,
  type RunFactorProjectionArgs,
} from "@macrohero/shared";

const DESCRIPTION = `Run a deterministic FX factor-sensitivity projection.

Given an FX pair, a horizon (days), and 1-8 factor shocks (name + direction +
severity tier), this fits an OLS regression of the pair on the factors over
the recent window and projects the pair's % move with a 95% confidence band.

You do NOT pick numerical magnitudes. The engine sizes every shock from the
factor's own realized volatility scaled to the horizon, using the severity
tier you choose:
  mild     -> 0.5-sigma move at the horizon
  moderate -> 1.0-sigma move at the horizon
  severe   -> 2.0-sigma move at the horizon
  extreme  -> 3.0-sigma move at the horizon

Factor names MUST come from the FACTOR_NAMES enum exactly (copy them
verbatim, no edits to capitalization or punctuation).`;

interface NumericsErrorEnvelope {
  pair: string;
  horizon_days: number;
  regression_window_days: number;
  r_squared: 0;
  intercept: 0;
  factors: [];
  projection: null;
  diagnostics: {
    n_observations: 0;
    warnings: [];
    error: { code: string; message: string };
  };
}

function errorEnvelope(
  args: RunFactorProjectionArgs,
  code: string,
  message: string,
): NumericsErrorEnvelope {
  return {
    pair: args.pair,
    horizon_days: args.horizon_days,
    regression_window_days: args.regression_window_days,
    r_squared: 0,
    intercept: 0,
    factors: [],
    projection: null,
    diagnostics: {
      n_observations: 0,
      warnings: [],
      error: { code, message: message.slice(0, 200) },
    },
  };
}

export const runFactorProjection = tool(
  async (raw: RunFactorProjectionArgs) => {
    // The args schema is enforced by tool() at the LangChain boundary, but
    // a defensive parse here applies defaults (regression_window_days).
    const args = runFactorProjectionArgsSchema.parse(raw);
    const url = `${process.env.NUMERICS_URL ?? "http://localhost:8001"}/v1/projection`;

    let res: Response;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(args),
        signal: AbortSignal.timeout(60_000),
      });
    } catch (err) {
      return errorEnvelope(
        args,
        "numerics_network_error",
        err instanceof Error ? err.message : String(err),
      );
    }

    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return errorEnvelope(
        args,
        "numerics_http_error",
        `HTTP ${res.status}: ${detail.slice(0, 120)}`,
      );
    }

    return res.json();
  },
  {
    name: "run_factor_projection",
    description: DESCRIPTION,
    schema: runFactorProjectionArgsSchema,
    verboseParsingErrors: true,
  },
);
