import { type NextRequest, NextResponse } from "next/server";

import { apiFetch } from "@/lib/api";

type Me = { user_id: string; timezone: string | null; show_thinking: boolean };

export async function GET() {
  try {
    const me = await apiFetch<Me>("/me");
    return NextResponse.json(me);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Unknown error" },
      { status: 502 },
    );
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const me = await apiFetch<Me>("/me", { method: "PATCH", body });
    return NextResponse.json(me);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Unknown error" },
      { status: 502 },
    );
  }
}
