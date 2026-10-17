// Phase 5: screens never call fetch directly; TypeScript types come from the Pydantic JSON Schema.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const root = join(__dirname, "..");

function files(dir: string): string[] {
  return readdirSync(join(root, dir)).flatMap((name) => {
    const rel = join(dir, name);
    return statSync(join(root, rel)).isDirectory() ? files(rel) : /\.(ts|tsx)$/.test(name) ? [rel] : [];
  });
}

describe("structure", () => {
  it("only lib/data calls fetch", () => {
    const offenders = [...files("app"), ...files("components"), ...files("lib")]
      .filter((f) => !f.startsWith(join("lib", "data")))
      .filter((f) => /\bfetch\s*\(/.test(readFileSync(join(root, f), "utf8")));
    expect(offenders).toEqual([]);
  });

  it("generated types come from the Pydantic schema", () => {
    const gen = readFileSync(join(root, "lib/types.gen.ts"), "utf8");
    expect(gen).toContain("Generated from the Pydantic schemas");
    for (const name of ["Finding", "ControlResult", "SkepticVerdict", "Citation", "ReasoningStep", "RunConfig"]) {
      expect(gen).toContain(`export interface ${name} {`);
    }
  });
});
