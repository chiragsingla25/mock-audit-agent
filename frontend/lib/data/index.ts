// The one data layer (spec Phase 5): screens import `data` from here and never call `fetch` directly.
import { liveSource } from "./live";
import { showcaseSource } from "./showcase";
import type { DataSource } from "./source";

export * from "./errors";
export type { DataSource } from "./source";

export const data: DataSource =
  process.env.NEXT_PUBLIC_MODE === "showcase"
    ? showcaseSource()
    : liveSource(process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000");
