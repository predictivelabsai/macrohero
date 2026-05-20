import { z } from "zod";

export const meResponseSchema = z.object({
  user_id: z.string(),
  display_name: z.string().nullable(),
  timezone: z.string().nullable(),
  show_thinking: z.boolean(),
});
export type MeResponse = z.infer<typeof meResponseSchema>;

export const meUpdateSchema = z
  .object({
    display_name: z.string().max(100).nullable().optional(),
    timezone: z.string().max(64).nullable().optional(),
    show_thinking: z.boolean().optional(),
  })
  .strict();
export type MeUpdate = z.infer<typeof meUpdateSchema>;
