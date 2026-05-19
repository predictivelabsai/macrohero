import { z } from "zod";
import { projectionResultSchema } from "./projection.js";

export const chatActionSchema = z.object({
  type: z.string(),
  id: z.string(),
  title: z.string(),
  url: z.string(),
});
export type ChatAction = z.infer<typeof chatActionSchema>;

export const chatPartSchema = z.discriminatedUnion("kind", [
  z.object({
    kind: z.literal("reasoning"),
    text: z.string(),
    // Outer multi-agent node that produced this bubble (supervisor /
    // research / analytics). Optional — older rows and non-streaming
    // origins won't have it.
    agent: z.string().optional(),
  }),
  z.object({
    kind: z.literal("text"),
    text: z.string(),
    agent: z.string().optional(),
  }),
  z.object({
    kind: z.literal("tool"),
    tool_name: z.string(),
    state: z.enum(["output-available", "output-error"]).default("output-available"),
    input: z.record(z.string(), z.unknown()).nullable().optional(),
    action_id: z.string().nullable().optional(),
    agent: z.string().optional(),
  }),
  z.object({ kind: z.literal("scenario_projection"), data: projectionResultSchema }),
]);
export type ChatPart = z.infer<typeof chatPartSchema>;
