"use client";
import { useSearchParams } from "next/navigation";

/** The run id from `?run=…` (query routing keeps the Phase 6 static export simple). */
export function useRunId(): string {
  return useSearchParams().get("run") ?? "";
}
