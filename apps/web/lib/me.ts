import { cache } from "react";

import { apiFetch } from "@/lib/api";

export type Me = {
  user_id: string;
  display_name: string | null;
  timezone: string | null;
};

/**
 * Per-request memoized fetch of the current user. React's `cache()` ensures we
 * only hit the API once per server render, regardless of how many components
 * call this.
 */
export const getMe = cache(async (): Promise<Me> => {
  try {
    return await apiFetch<Me>("/me");
  } catch {
    // Resilient default — the rest of the page should still render even if
    // /me is briefly unavailable. Times will just fall back to UTC.
    return { user_id: "", display_name: null, timezone: null };
  }
});

export async function getUserTimezone(): Promise<string> {
  const me = await getMe();
  return me.timezone ?? "UTC";
}
