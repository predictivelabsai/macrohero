"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiFetch } from "@/lib/api";

export async function deleteSessionAction(id: string, isCurrent: boolean): Promise<void> {
  await apiFetch<unknown>(`/chat/sessions/${id}`, { method: "DELETE" });
  revalidatePath("/chat", "layout");
  if (isCurrent) {
    redirect("/chat");
  }
}
