// Phase 6: the static showcase source reads the exported JSON under the Pages base path and is read-only.
import { describe, expect, it } from "vitest";
import { showcaseSource } from "@/lib/data/showcase";

describe("showcase data source", () => {
  it("reads index and run files under the base path", async () => {
    const urls: string[] = [];
    const src = showcaseSource("/mock-audit-agent", (url) => {
      urls.push(String(url));
      return Promise.resolve(new Response(String(url).endsWith(".md") ? "# report" : JSON.stringify({ runs: [] })));
    });
    expect(src.mode).toBe("showcase");
    await src.getIndex();
    await src.listAudits();
    await src.getFindings("r1");
    await src.getReport("r1");
    await src.getReportMarkdown("r1");
    expect(urls).toEqual([
      "/mock-audit-agent/data/index.json", "/mock-audit-agent/data/runs/r1/findings.json",
      "/mock-audit-agent/data/runs/r1/report.json", "/mock-audit-agent/data/runs/r1/report.md",
    ]);   // index.json is fetched once and reused
  });

  it("can't start audits or submit reviews", async () => {
    const src = showcaseSource("", () => Promise.reject(new Error("no network")));
    await expect(src.startAudit("base", "agent")).rejects.toThrow(/static showcase/);
    await expect(src.submitReview("r1", [])).rejects.toThrow(/static showcase/);
  });

  it("reports an unpublished run plainly", async () => {
    const src = showcaseSource("", () => Promise.resolve(new Response("", { status: 404 })));
    await expect(src.getAudit("nope")).rejects.toThrow("This run isn't published.");
  });
});
