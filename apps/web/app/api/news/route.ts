import { NextResponse } from "next/server";

import { fetchAllNews } from "@/lib/news";

export const dynamic = "force-dynamic";

export async function GET() {
  const items = await fetchAllNews();
  return NextResponse.json(
    { items },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
