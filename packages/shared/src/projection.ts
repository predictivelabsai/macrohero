import { z } from "zod";

export const factorContributionSchema = z.object({
  name: z.string(),
  ticker: z.string(),
  beta: z.number(),
  expected_change: z.number(),
  unit: z.string(),
  contribution_pct: z.number(),
  se: z.number(),
  t_stat: z.number(),
  p_value: z.number(),
  ci_low: z.number(),
  ci_high: z.number(),
  vif: z.number(),
  severity: z.string().optional(),
  direction: z.string().optional(),
  sigma_multiple: z.number().optional(),
});

export const projectionSchema = z.object({
  point_pct: z.number(),
  band_95_low_pct: z.number(),
  band_95_high_pct: z.number(),
  spot_at_t0: z.number(),
  projected_spot: z.number(),
  spot_band_low: z.number(),
  spot_band_high: z.number(),
  residual_variance_pct2: z.number(),
  parameter_variance_pct2: z.number(),
});

export const projectionResultSchema = z.object({
  pair: z.string(),
  horizon_days: z.number().int(),
  regression_window_days: z.number().int(),
  r_squared: z.number(),
  intercept: z.number(),
  factors: z.array(factorContributionSchema),
  projection: projectionSchema.nullable(),
  diagnostics: z.object({
    n_observations: z.number(),
    warnings: z.array(z.string()),
    error: z
      .object({
        code: z.string(),
        message: z.string(),
      })
      .nullable(),
  }).passthrough(),
});
export type ProjectionResult = z.infer<typeof projectionResultSchema>;
