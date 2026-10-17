import { Suspense } from "react";
import { FindingsScreen } from "@/components/FindingsScreen";

// Reads ?run= on the client (useSearchParams), so it sits inside a Suspense boundary.
export default function Page() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <FindingsScreen />
    </Suspense>
  );
}
