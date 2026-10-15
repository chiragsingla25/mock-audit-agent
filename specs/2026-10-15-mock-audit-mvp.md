# Spec — Mock Audit Agent MVP

Date: 2026-10-15 · Source: [docs/proposal.md](../docs/proposal.md) (approved 2026-10-15) · Builder: app-developer
Scope rule: **MVP only.** Anything not in a phase below goes to the README "Roadmap"; anything that needs it is a flag-back to app-architect.

## 1. Goal

Show, with measured numbers, that a cheap two-LLM LangGraph agent finds the planted SOC 2 gaps in a synthetic company, cites real records, avoids traps that fool a rules-only run, and costs cents per audit. It also has to be reviewable in a local app and browsable on a static GitHub Pages site.

## 2. Prior art and scope rationale

- **Copying:** Hyperproof's "AI suggests, human validates" review; Thoropass's "forecast before fieldwork"; evidence-linked findings with citations (table stakes for every competitor).
- **Our angle:** populations and samples, auditor-format findings, and accuracy measured against an answer key and a rules-only baseline.
- **Out of scope (roadmap):** recipe planner, skeptic escalation and reruns, sample extension, citation repair, the skeptic reviewing dismissals, the write-up judge, C6 observations, screenshots and vision, SQL over exports, an evaluation screen in the UI, cross-control checks, multi-framework support, live integrations, auth, hosting live audits online.

## 3. Fixed decisions (do not re-open)

- Stack: LangGraph + LangChain `create_agent`, OpenRouter via `langchain-openrouter`, FastAPI (local), Next.js (live + static showcase), GitHub Pages; LangSmith tracing.
- Models: tester `qwen/qwen3.8-flash`, skeptic `deepseek/deepseek-v4-flash` (different family). Phase 0 may swap the tester to `qwen/qwen3.5-flash-02-23`. Any other model change is a flag-back.
- US$10 hard cap overall; a run stops at US$1 and the project stops at US$9.50.
- Observation period 2025-10-01 to 2026-09-30. C2 "24 hours" = 24 clock hours. C3/C5 sign-off within 10 business days of quarter end. Compare all timestamps in UTC.
- Readiness, never an audit opinion; no pass badge; every finding cites ≥ 1 existing record id.
- Severity comes only from the 7 rules in architecture.md §6.

## 4. Interfaces

- `backend/src/mockaudit/schemas.py`: `ControlSpec`, `TestStep`, `EvidenceSource`, `Citation`, `Candidate`, `Finding`, `Dismissal`, `ReasoningStep`, `ControlResult`, `SkepticVerdict`, `RunConfig` (Pydantic).
- `controls.yaml` → `ControlSpec` × 12. `CHECKS: dict[str, Callable]` registry (plain dict).
- Graph: `AuditState` (TypedDict with reducers), control subgraph `ControlState`, nodes as in proposal §4.
- CLI `mockaudit`: `gen`, `run`, `eval`, `export-showcase`.
- Run artifacts: `runs/<run_id>/{controls/<id>.json, verdicts.json, report.md, report.json, eval.json}`; spend in `runs/spend.jsonl`.
- API (local): `POST /audits`, `GET /audits/{id}`, `GET /audits/{id}/findings`, `POST /audits/{id}/review` (resumes the `interrupt`), `GET /audits/{id}/report`.
- Showcase JSON: `frontend/public/data/` (index, runs, controls, findings, cited records, report, eval summary).

## 5. Phased build plan

Milestone 1 = Phases 0–4. Milestone 2 = Phases 5–6. Record `Milestone N base: <commit>` here when each starts. Extra fresh-context review gates come after Phase 1 and Phase 3.

### Phase 0: MVP notebook (validate the idea)
Delivers `notebooks/mvp.ipynb`: C2 end to end on hand-built rows (about 20 terminations, 2 late, 1 missing, 1 trap), covering population check → checks → tester (tool loop + structured output) → skeptic, for 2 tester models × 3 repeats, with cost measured.
- [x] The notebook runs top to bottom with real OpenRouter calls, on the Mac (the real environment).
- [x] A per-model table shows: late revocations found (target 2/2), missing termination found (1/1), trap dismissed (yes/no), invented citations (target 0), tokens and US$ per control.
- [x] One reasoning step list is printed from the tester's messages.
- [x] A projected US$ per 12-control audit is computed. If it's over US$0.40, stop and flag back (budget plan).
- [x] Failure case: a tester output that fails schema validation is retried once with the error, and the result is shown.

Result 2026-10-15 (run `mvp-20261015T103418Z`, the third real run; earlier runs exposed the bugs in Deviations):

| Tester | Runs OK | Late 2/2 | Missing 1/1 | Trap dismissed | Invented cites | US$/control (OK runs) | Projected US$/audit |
|---|---|---|---|---|---|---|---|
| qwen3.8-flash (reasoning off) | 2/3 (1 upstream 429) | 2, 2 | 1, 1 | yes, yes | 0 | 0.0034 | ≈ 0.041 |
| qwen3.5-flash-02-23 | 3/3 | 2, 2, 2 | 1, 1, 1 | yes ×3 | 0 | 0.0030 | 0.036 |

Both are about 10× under the US$0.40 line. Latency is 80–175 s per control (DeepSeek skeptic calls are the slow part). Phase 0 total spend was US$0.067.

Clarified 2026-10-15 (Phase 0 clarify pass):
- G2 = a terminated employee who **has** an Okta account (a create event) but never gets a suspend/deactivate event. A contractor who was never provisioned is a noise row: code excludes them because they have no Okta account, records a note, and raises no finding (handover §11).
- Trap = employee→contractor conversion: HR terminates the employee and rehires them as a contractor the same day, so access legitimately continues. Code flags it as late or never revoked. The tester should dismiss it using the rehire record and `ask_owner`.
- Reasoning effort for both models is `low`.
- Projected US$ per audit = mean C2 cost (tester + skeptic calls for its findings) × 12.
- The retry-once failure case is shown with a stub model whose first output is invalid. Real-run retries are also counted in the table.

Verify: run `notebooks/mvp.ipynb` → you see the per-model table and the projected cost per audit.
After Phase 0, record the chosen tester in §3 and in Deviations.

### Phase 1: Schemas and Ledgerly dataset **[review gate]**
Delivers the schemas, `controls.yaml` (12 controls with hand-written recipes), a seeded generator `mockaudit gen`, the answer key, about 4 traps, and variants A and B.
- [ ] `mockaudit gen --variant base --seed 7` writes `data/ledgerly/base/` (controls.yaml, policies/, exports/, artifacts/, answers.yaml, answer_key.yaml). Running it twice gives byte-identical files.
- [ ] The answer key lists G1–G10 (each tagged `code` or `judgment`), the traps, and clean controls C1, C4, C9, C11. Severities are computed by the 7 rules.
- [ ] Every gap and trap has a documented query in `tests/test_dataset.py` that finds it in the raw files.
- [ ] Noise is present: name-format mismatches, mixed time zones (AEST HR, UTC Okta), a same-day suspension followed by a later deletion (not a gap), a compliant emergency change, and a scan run late in the same week (not a gap).
- [ ] The domain-rule edges from handover §11 have a dataset row and a test: Friday 18:00 → Monday 09:00 is an exception; exactly 30 days passes and 31 fails; a Dec 15 hire trained Jan 10 passes.
- [ ] Variants A and B re-plant gaps in different combinations, and their answer keys match.
- [ ] Failure case: an invalid `controls.yaml` entry raises a validation error naming the control and the field.

Verify: `uv run mockaudit gen --variant base && uv run pytest tests/test_dataset.py` → all pass.

### Phase 2: Checks and scoring
Delivers the `CHECKS` registry (the checks the 12 recipes need), the 7 severity rules, the citation check, the scorer, and `run --checks-only`.
- [ ] Each check has unit tests, including both edges of its threshold.
- [ ] `run --checks-only` raises every candidate (check failures plus items missing from the population) with citations, and uses no LLM.
- [ ] The scorer reports recall, precision, clean-control accuracy, citation validity and severity agreement against the answer key, matching on control id and ≥ 1 cited record id.
- [ ] Checks-only on base finds every `code`-tagged gap and raises every trap (expected low precision).
- [ ] Failure case: a citation to a nonexistent record id is dropped and logged by the citation check.

Verify: `uv run mockaudit run --checks-only --variant base && uv run mockaudit eval --run latest` → a metrics table is printed.

### Phase 3: Audit graph **[review gate]**
Delivers the full `StateGraph`: load → dispatch (`Send` × 12, `max_concurrency`) → control subgraph (population_check → run_checks → sample → tester → finalize) → skeptic fan-out → route (max 1 revise round, entering at `tester`) → severity → human_review (`interrupt`, or skipped when `review_mode=skip`) → report. Also the SQLite checkpointer, LangSmith tracing, the spend guard and the reasoning steps.
- [ ] `mockaudit run --variant base --review skip` produces 12 control result files and a report.
- [ ] Findings merge by `finding_id`; a revised control keeps its kept findings unchanged (test with a stub LLM).
- [ ] At least one revise round appears in LangSmith on base, or in a stub test if the real run doesn't produce one.
- [ ] Nothing to review → goes straight to severity (stub test with a clean control set).
- [ ] An exception or timeout in one control gives `status: error` for that control only; the other 11 complete (stub test).
- [ ] Spend over the run cap stops new LLM calls and marks the remaining controls `error: spend_cap` (stub test).
- [ ] Every finding and dismissal carries reasoning steps (`check` / `tool` / `owner` / `llm` / `rule`).
- [ ] `--review human` pauses at `human_review`; resuming with decisions gives a report containing only approved findings.

Verify: `uv run mockaudit run --variant base --review skip` → `runs/<id>/` is complete, the cost is printed, and the trace is visible in LangSmith.

### Phase 4: Evaluation and CI (end of Milestone 1)
- [ ] `mockaudit eval --all` runs base + variants A and B (agent), skeptic-off (from the same runs, with no extra calls), checks-only, and 3 stability runs on base. It writes `eval.json` and a Markdown table.
- [ ] Reports recall, precision, clean-control accuracy, citation validity, severity agreement, stability overlap, agent vs checks-only, skeptic on vs off, and US$ and tokens per audit.
- [ ] Total evaluation spend ≤ US$2.00 (from `spend.jsonl`).
- [ ] `.github/workflows/ci.yml`: ruff + pytest + showcase JSON validation, with no secrets and no LLM calls.
- [ ] Targets are reported honestly. Missing one is not a fail; hiding it is.

Verify: `uv run mockaudit eval --all` → `eval.json` + table; CI is green on push.

### Phase 5: Local app (FastAPI + Next.js live mode)
Four screens, as in the 2026-10-15 mockup:
1. **Start:** dataset, mode (agent / skeptic off / checks only), models (read-only), spend so far, Start audit.
2. **Progress:** 12 control cards (queued → running → done / error), polled every second; totals and cost.
3. **Findings:** a list (findings, "not raised", "rejected by skeptic") and a detail view (condition, criteria, cause, effect, recommendation, citations with the cited rows shown inline, reasoning step list, skeptic verdict, severity), plus approve / dismiss with a note.
4. **Report:** approved findings, coverage per control, remediation tasks; export Markdown and JSON; no pass badge.
- [ ] One data layer (`NEXT_PUBLIC_MODE=live|showcase`); screens never call `fetch` directly.
- [ ] TypeScript types are generated from the Pydantic JSON Schema.
- [ ] Submitting the review resumes the paused graph, and the report shows only approved findings.
- [ ] Failure case: starting an audit with the API down shows "Can't reach the local API. Start it with `uv run mockaudit serve`."

Verify: start an audit in the browser → 12 cards finish → open G1 → the step list shows → approve → export Markdown.

### Phase 6: Showcase and ship (end of Milestone 2)
- [ ] `mockaudit export-showcase <run_ids>` writes the showcase JSON (cited records only, not full exports), and it validates against the schemas.
- [ ] A static export (`output: 'export'`, `basePath`, `generateStaticParams`) builds; the Pages site has no start button and shows recorded review decisions.
- [ ] `.github/workflows/pages.yml` deploys on push to `main`.
- [ ] README: what it is, the diagram, evaluation results (including agent vs checks-only), cost, how to run locally, the roadmap, and the note on synthetic data and practitioner review.
- [ ] A 2-minute video script is in `docs/video-script.md`.

Verify: push to `main` → the Pages URL shows the runs, findings with step lists, and the comparison.

## 6. Verification (overall)

Golden answer key with code-scored metrics (proposal §7), unit tests per criterion, no LLM in CI, fresh-context reviews after Phase 1, after Phase 3 and at each milestone.

## Deviations from spec

- [phase 0] `ChatOpenRouter.request_timeout` is in **milliseconds** (it maps to the SDK's `timeout_ms`). Passing `120` gave a 120 ms timeout, and the OpenRouter SDK's own backoff loop then retried silently and hung with no error — library surprise — resolved by passing `request_timeout=120_000`. Carry this into Phase 3's model factory.
- [phase 0] `ToolStrategy` makes `create_agent` bind tools with `tool_choice="any"` (sent as `required`). Alibaba rejects that for `qwen/qwen3.8-flash` in thinking mode (`400 invalid_parameter_error: tool_choice ... does not support being set to required ... in thinking mode`), so every qwen3.8 tester call failed with `reasoning.effort=low` — library/provider gap — resolved by running qwen3.8 with `reasoning: {enabled: false}` (per-model override). This differs from the clarify answer "low for both"; qwen3.5 already returns 0 reasoning tokens.
- [phase 0] The notebook's first scorer matched on exact `candidate_id`s, and one run that echoed record ids scored 0/2 despite raising both — builder bug, stricter than the spec's "control id + ≥ 1 cited record id" rule — resolved by resolving candidate ids and cited HR record ids to candidates. Phase 2's scorer should match on record ids from the start.
- [phase 0] The notebook's US$/control for qwen3.8 averages over all 3 runs, including the 429 failure at US$0, which shows 0.0023 (≈ 0.027/audit). Over the OK runs it is 0.0034 (≈ 0.041/audit), and the spec table uses that figure — builder reporting bug, left in the executed notebook (scratch) — Phase 4's cost metric must average over successful runs.
- [phase 0] Control latency is 80–175 s against `CONTROL_TIMEOUT_S=180` in `.env.example`, which leaves almost no headroom — found in measurement — Phase 3 should raise the timeout (or cap skeptic latency) before the full graph runs.
- [phase 0] `qwen/qwen3.8-flash` returned an upstream 429 (Alibaba rate limit) on 1 of 3 runs — provider capacity — not resolved here; it's an input to the tester choice.
