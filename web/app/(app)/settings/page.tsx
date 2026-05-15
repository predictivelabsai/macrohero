import { getMe } from "@/lib/me";

import { TimezoneCard } from "./timezone-card";

export default async function SettingsPage() {
  const me = await getMe();

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Display preferences for MacroHero.
          </p>
        </div>
        <TimezoneCard currentTimezone={me.timezone} />
      </div>
    </div>
  );
}
