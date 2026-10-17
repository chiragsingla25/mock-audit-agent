// Phase 5: the one data layer, and the API-down failure case.
import { describe, expect, it } from "vitest";
import { API_DOWN_MESSAGE, ApiError, ApiUnreachableError } from "@/lib/data/errors";
import { liveSource } from "@/lib/data/live";

const reply = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));

describe("live data source", () => {
  it("maps a connection failure to the exact API-down message", async () => {
    const src = liveSource("http://127.0.0.1:8000", () => Promise.reject(new TypeError("Failed to fetch")));
    await expect(src.startAudit("base", "agent")).rejects.toThrow(ApiUnreachableError);
    await expect(src.getConfig()).rejects.toThrow(API_DOWN_MESSAGE);
    expect(API_DOWN_MESSAGE).toBe("Can't reach the local API. Start it with `uv run mockaudit serve`.");
  });

  it("surfaces the API's error detail with its status", async () => {
    const src = liveSource("http://x", () => reply(409, { detail: "an audit is already running" }));
    const err = await src.startAudit("base", "agent").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.message).toBe("an audit is already running");
  });

  it("calls the documented endpoints", async () => {
    const calls: [string, string][] = [];
    const src = liveSource("http://x", (url, init) => {
      calls.push([String(url), init?.method ?? "GET"]);
      return reply(200, { run_id: "r1" });
    });
    await src.startAudit("a", "checks_only");
    await src.getAudit("r1");
    await src.getFindings("r1");
    await src.submitReview("r1", [{ finding_id: "C2-timeliness", decision: "approve", note: "" }]);
    await src.getReport("r1");
    expect(calls).toEqual([
      ["http://x/audits", "POST"], ["http://x/audits/r1", "GET"], ["http://x/audits/r1/findings", "GET"],
      ["http://x/audits/r1/review", "POST"], ["http://x/audits/r1/report", "GET"],
    ]);
  });
});
