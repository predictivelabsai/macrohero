export type FactorContribution = {
  name: string;
  ticker: string;
  beta: number;
  expected_change: number;
  unit: "%" | "bp";
  contribution_pct: number;
  // Qualitative inputs from the LLM; magnitudes (expected_change) are derived
  // by the engine from realized vol, not chosen by the LLM.
  severity?: "mild" | "moderate" | "severe" | "extreme" | "";
  direction?: "up" | "down" | "";
  sigma_multiple?: number; // signed: e.g. -2.0 for "down severe"
};

export type Projection = {
  point_pct: number;
  band_95_low_pct: number;
  band_95_high_pct: number;
  spot_at_t0: number;
  projected_spot: number;
  spot_band_low: number;
  spot_band_high: number;
};

export type ProjectionDiagnostics = {
  n_observations: number;
  warnings: string[];
  error: { code: string; message: string } | null;
};

export type ProjectionResult = {
  pair: string;
  horizon_days: number;
  regression_window_days: number;
  r_squared: number;
  intercept: number;
  factors: FactorContribution[];
  projection: Projection | null;
  diagnostics: ProjectionDiagnostics;
};
