/**
 * Time-of-day greeting computed in the user's own timezone.
 *
 * Buckets:
 *   05:00 – 11:59  → "Good morning"
 *   12:00 – 16:59  → "Good afternoon"
 *   17:00 – 21:59  → "Good evening"
 *   22:00 – 04:59  → "Good night"
 *
 * Falls back to "Hello" if the timezone string is invalid.
 */
export function timeOfDayGreeting(timezone: string | null | undefined): string {
  const tz = timezone || "UTC";
  let hour: number;
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hour: "numeric",
      hour12: false,
    }).formatToParts(new Date());
    const hourPart = parts.find((p) => p.type === "hour")?.value ?? "0";
    // hour12:false sometimes yields "24" for midnight; normalize to 0.
    hour = Number.parseInt(hourPart, 10) % 24;
    if (!Number.isFinite(hour)) return "Hello";
  } catch {
    return "Hello";
  }
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 17) return "Good afternoon";
  if (hour >= 17 && hour < 22) return "Good evening";
  return "Good night";
}
