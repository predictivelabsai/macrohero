import { z } from "zod";
import { FACTOR_NAMES } from "./factors.gen.js";

export { FACTOR_NAMES, type FactorName } from "./factors.gen.js";

export const directionSchema = z.enum(["up", "down"]);
export const severitySchema = z.enum(["mild", "moderate", "severe", "extreme"]);

export const factorShockSchema = z.object({
  name: z.enum(FACTOR_NAMES),
  direction: directionSchema,
  severity: severitySchema,
});
export type FactorShock = z.infer<typeof factorShockSchema>;

export const runFactorProjectionArgsSchema = z.object({
  pair: z.string().min(1),
  horizon_days: z.number().int().min(1).max(90),
  factors: z.array(factorShockSchema).min(1).max(8),
  regression_window_days: z.number().int().min(60).max(1000).default(252),
});
export type RunFactorProjectionArgs = z.infer<typeof runFactorProjectionArgsSchema>;
