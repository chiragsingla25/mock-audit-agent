import { ShowcaseHome } from "@/components/ShowcaseHome";
import { StartScreen } from "@/components/StartScreen";
import { data } from "@/lib/data";

// Live mode starts audits; the static showcase has no start button and lists published runs instead.
export default function Page() {
  return data.mode === "showcase" ? <ShowcaseHome /> : <StartScreen />;
}
