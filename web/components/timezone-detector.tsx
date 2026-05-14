"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

/**
 * Best-effort timezone autodetect. On the first authed page load where the
 * user has no stored timezone, read the browser's IANA zone and PATCH /me.
 * Renders nothing.
 */
export function TimezoneDetector({ currentTimezone }: { currentTimezone: string | null }) {
  const router = useRouter();
  const triedRef = useRef(false);

  useEffect(() => {
    if (currentTimezone) return;
    if (triedRef.current) return;
    triedRef.current = true;

    let detected: string;
    try {
      detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return;
    }
    if (!detected) return;

    fetch("/api/me", {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ timezone: detected }),
    })
      .then((r) => {
        if (r.ok) router.refresh();
      })
      .catch(() => {
        // Silently ignore — the next render will retry on mount.
      });
  }, [currentTimezone, router]);

  return null;
}
