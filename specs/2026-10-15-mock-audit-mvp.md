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
- Models: tester `qwen/qwen3.5-flash-02-23` (chosen after Phase 0, 2026-10-15; was `qwen/qwen3.8-flash`), skeptic `deepseek/deepseek-v4-flash` (different family). Any other model change is a flag-back.
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

Milestone 1 = Phases 0–4. Milestone 2 = Phases 5–6. Record `Milestone N base: <commit>` here when each starts.
Milestone 1 base: 0bdd115 (scaffold + Phase 0 notebook; the notebook is scratch and is not reviewed). Extra fresh-context review gates come after Phase 1 and Phase 3.
Milestone 2 base: 03b17b0 (2026-10-17). Release-qa for Milestone 1 was deferred by Chirag ("skip release-qa for now"), so it is still owed before shipping.

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
- [x] `mockaudit gen --variant base --seed 7` writes `data/ledgerly/base/` (controls.yaml, policies/, exports/, artifacts/, answers.yaml, answer_key.yaml). Running it twice gives byte-identical files.
- [x] The answer key lists G1–G10 (each tagged `code` or `judgment`), the traps, and clean controls C1, C4, C9, C11. Severities are computed by the 7 rules.
- [x] Every gap and trap has a documented query in `tests/test_dataset.py` that finds it in the raw files.
- [x] Noise is present: name-format mismatches, mixed time zones (AEST HR, UTC Okta), a same-day suspension followed by a later deletion (not a gap), a compliant emergency change, and a scan run late in the same week (not a gap).
- [x] The domain-rule edges from handover §11 have a dataset row and a test: Friday 18:00 → Monday 09:00 is an exception; exactly 30 days passes and 31 fails; a Dec 15 hire trained Jan 10 passes.
- [x] Variants A and B re-plant gaps in different combinations, and their answer keys match.
- [x] Failure case: an invalid `controls.yaml` entry raises a validation error naming the control and the field.

Clarified 2026-10-15/16 (Phase 1 clarify pass, ruled by Chirag):
- Traps (4): T1 C2 employee→contractor conversion (from Phase 0); T2 C1 access granted before the approval timestamp, but for a birthright role the policy pre-approves; T3 C8 critical vuln open > 30 days with a signed risk acceptance; T4 C9 alert ticket with no post-incident review, closed as "not an incident". T2 and T4 sit in clean controls.
- Tags: G3 (Q3 access-review sheet without sign-off) and G10 (restore test report dated before the period) are `judgment`. They live in `artifacts/` documents, so checks-only can find at most 8/10. The other 8 are `code`.
- A C3/C5 sign-off within 10 business days of quarter end passes even when dated after 2026-09-30. `date_in_period` doesn't apply to sign-off dates.
- Variants A and B each use their own seed and plant 7 of the 10 gaps on different records, dates and counts. Controls whose gaps were dropped become clean, and traps are re-placed. Each variant's answer key is generated from its own data, and the dataset tests run on base, A and B.
- G1 = 2 of 18 late: the Friday 18:00 → Monday 09:00 case (63 h, the handover §11 edge) and a 9-day one. It stays 11% (high). This replaces "5 and 9 days".
- The 30/31-day edge lives in C10: one G9 trainee is exactly 31 days after hire (fails), and another hire at exactly 30 days passes. C8 gets a critical closed at exactly 30 days (passes). G8 stays a single 47-day breach.
- Scale follows research.md §4 (about 120 employees, 30 hires, 18 terminations, about 900 deploys, 52 weekly scans) inside the spec's period, not research.md's calendar year.

Verify: `uv run mockaudit gen --variant base && uv run pytest tests/test_dataset.py` → all pass.

### Phase 2: Checks and scoring
Delivers the `CHECKS` registry (the checks the 12 recipes need), the 7 severity rules, the citation check, the scorer, and `run --checks-only`.
- [x] Each check has unit tests, including both edges of its threshold.
- [x] `run --checks-only` raises every candidate (check failures plus items missing from the population) with citations, and uses no LLM.
- [x] The scorer reports recall, precision, clean-control accuracy, citation validity and severity agreement against the answer key, matching on control id and ≥ 1 cited record id.
- [x] Checks-only on base finds every `code`-tagged gap and raises every trap (expected low precision).
- [x] Failure case: a citation to a nonexistent record id is dropped and logged by the citation check.

Clarified 2026-10-16 (Phase 2 clarify pass):
- Scoring unit (ruled by Chirag): one finding per (control, test step), grouping that step's failed records. The tester produces the same shape. Matching is on control id + ≥ 1 cited record id. A separate metric, **traps raised**, counts traps whose record is cited in a kept finding, because a trap merged into a true finding (T1 into G1, T3 into G8) is otherwise invisible to precision. Expected on base checks-only: recall 8/10 (G3/G10 are judgment), precision about 8/10, clean-control accuracy 2/4 (T2 and T4 make C1/C9 look gapped), traps raised 4/4.
- Defaults (builder, stated):
  - Limits are inclusive: 24.0 h, 30 days and 2 business days all pass. Rule 4 is strict (> 10%).
  - C2 measures elapsed UTC hours. C8 and C10 count calendar dates. C7 counts business days on UTC dates.
  - A missing ISO week is one candidate that cites the nearest scans before and after it.
  - Judgment-only steps are listed in coverage as `not_tested` in checks-only mode.
- Metrics:
  - **Recall:** gaps matched / planted gaps, with code-tagged recall shown separately.
  - **Precision:** matching kept findings / kept findings.
  - **Clean-control accuracy:** clean controls with no kept finding / clean controls.
  - **Citation validity:** valid citations / all citations, counting the ones the citation check dropped.
  - **Severity agreement:** matched pairs where the rule severity equals the key severity.
  - **Traps raised:** as defined above.
- Each recipe step declares its `gap_type` in controls.yaml, so a failed step maps to a finding type without an LLM.

Verify: `uv run mockaudit run --checks-only --variant base && uv run mockaudit eval --run latest` → a metrics table is printed.

### Phase 3: Audit graph **[review gate]**
Delivers the full `StateGraph`: load → dispatch (`Send` × 12, `max_concurrency`) → control subgraph (population_check → run_checks → sample → tester → finalize) → skeptic fan-out → route (max 1 revise round, entering at `tester`) → severity → human_review (`interrupt`, or skipped when `review_mode=skip`) → report. Also the SQLite checkpointer, LangSmith tracing, the spend guard and the reasoning steps.
- [x] `mockaudit run --variant base --review skip` produces 12 control result files and a report.
- [x] Findings merge by `finding_id`; a revised control keeps its kept findings unchanged (test with a stub LLM).
- [x] At least one revise round appears in LangSmith on base, or in a stub test if the real run doesn't produce one.
- [x] Nothing to review → goes straight to severity (stub test with a clean control set).
- [x] An exception or timeout in one control gives `status: error` for that control only; the other 11 complete (stub test).
- [x] Spend over the run cap stops new LLM calls and marks the remaining controls `error: spend_cap` (stub test).
- [x] Every finding and dismissal carries reasoning steps (`check` / `tool` / `owner` / `llm` / `rule`).
- [x] `--review human` pauses at `human_review`; resuming with decisions gives a report containing only approved findings.

Clarified 2026-10-16 (Phase 3 clarify pass, ruled by Chirag):
- `sample`: for judgment-only steps the tester sees every item, up to a cap of 25. Beyond that it takes a seeded random 25. Sampling can't make G3 or G10 a matter of luck.
- The skeptic reviews **every** finding, including code-only (`judge: none`) ones. A rejected code-proven finding is reported as rejected; nothing hides it.
- `CONTROL_TIMEOUT_S=420` (Phase 0 measured 80–175 s per control).
- `--review human` writes `runs/<id>/review_request.json` at the pause, and `mockaudit review --run <id> --decisions <file>` resumes it. Each finding gets approve or dismiss plus a note. The Phase 5 API reuses this.
- Defaults (builder, stated):
  - Failures of `judge: none` steps become code findings directly. Candidates from `judge: llm` steps go to the tester, which raises or dismisses each one.
  - A control with no LLM candidates and no judgment-only steps makes no LLM call.
  - Counts are set by code. For tester findings, exceptions are the candidates covered, resolved by candidate id or cited record id, and `tested` comes from the check. For judgment-only steps, exceptions are the distinct sampled items cited, and `tested` is the sample size.
  - Revise round: only the revised finding ids go back to the tester, along with the skeptic's reason. Each comes back with the same `finding_id`, or is dismissed. Anything still marked `revise` after 1 round becomes `unresolved`.
  - Skip-mode report: kept and unresolved findings (unresolved marked as such), plus a "rejected by skeptic" list. Human mode: approved findings only.
  - Spend guard: checked before every LLM call. Over the run cap, the control errors with `spend_cap`.
  - Checks-only and skeptic-off are run-config modes of the same graph.

Verify: `uv run mockaudit run --variant base --review skip` → `runs/<id>/` is complete, the cost is printed, and the trace is visible in LangSmith.

### Phase 4: Evaluation and CI (end of Milestone 1)
- [x] `mockaudit eval --all` runs base + variants A and B (agent), skeptic-off (from the same runs, with no extra calls), checks-only, and 3 stability runs on base. It writes `eval.json` and a Markdown table.
- [x] Reports recall, precision, clean-control accuracy, citation validity, severity agreement, stability overlap, agent vs checks-only, skeptic on vs off, and US$ and tokens per audit.
- [x] Total evaluation spend ≤ US$2.00 (from `spend.jsonl`).
- [x] `.github/workflows/ci.yml`: ruff + pytest + showcase JSON validation, with no secrets and no LLM calls. (The showcase step moved to Phase 6 by ruling. First run green: https://github.com/chiragsingla25/mock-audit-agent/actions/runs/38891182571)
- [x] Targets are reported honestly. Missing one is not a fail; hiding it is.

Clarified 2026-10-16 (Phase 4 clarify pass, ruled by Chirag):
- Stability: 3 base agent runs in total (the main base run plus 2). Overlap is the mean pairwise Jaccard of each run's kept-finding keys `(control_id, test_step)`, and recall per run is shown alongside.
- The showcase-JSON validation step in CI moves to Phase 6, where `export-showcase` creates the JSON. Phase 4's ci.yml runs ruff + pytest.
- CI is verified for real: create a public GitHub repo with `gh` under Chirag's account, push `main`, and check the Actions run.
- Defaults (builder, stated):
  - **Skeptic-off view:** the same agent runs scored as if the skeptic hadn't run. Every finding the tester raised counts, whatever the skeptic said (rejected and unresolved included). A revised finding counts in its revised form. There are no extra calls.
  - **Checks-only:** runs on base, a and b (free).
  - **Eval cap:** `EVAL_SPEND_CAP_USD=2.00`. Before each agent run, the harness stops if eval spend so far plus the dearest run so far would exceed the cap, and records the skipped runs.
  - **Outputs:** `runs/eval-<ts>/eval.json` and `eval.md`, plus the printed table. Each target is marked met or missed, and a missed target is shown, never hidden.

Verify: `uv run mockaudit eval --all` → `eval.json` + table; CI is green on push.

### Phase 5: Local app (FastAPI + Next.js live mode)
Four screens, as in the 2026-10-15 mockup:
1. **Start:** dataset, mode (agent / skeptic off / checks only), models (read-only), spend so far, Start audit.
2. **Progress:** 12 control cards (queued → running → done / error), polled every second; totals and cost.
3. **Findings:** a list (findings, "not raised", "rejected by skeptic") and a detail view (condition, criteria, cause, effect, recommendation, citations with the cited rows shown inline, reasoning step list, skeptic verdict, severity), plus approve / dismiss with a note.
4. **Report:** approved findings, coverage per control, remediation tasks; export Markdown and JSON; no pass badge.
- [x] One data layer (`NEXT_PUBLIC_MODE=live|showcase`); screens never call `fetch` directly.
- [x] TypeScript types are generated from the Pydantic JSON Schema.
- [x] Submitting the review resumes the paused graph, and the report shows only approved findings.
- [x] Failure case: starting an audit with the API down shows "Can't reach the local API. Start it with `uv run mockaudit serve`."

Clarified 2026-10-17 (Phase 5 clarify pass, ruled by Chirag):
- No 2026-10-15 mockup exists in the repo or the artifacts, so the screens are built from this phase's list and PRD §9. Screenshots are shown at the gate.
- Audits started from the browser always use `review_mode: human`. `--review skip` stays a CLI/eval option.
- Styling: Tailwind CSS 4, no component library.
- Verification: API tests with stub LLMs (FastAPI TestClient), Vitest for the data layer and the API-down message, then the Verify line done by hand in the built-in browser with one real audit (about US$0.03), with screenshots.
- Defaults (builder, stated):
  - **API:** `mockaudit serve` on 127.0.0.1:8000, with CORS for localhost:3000.
  - **Endpoints:** spec §4's five, plus `GET /config` (models, spend so far, variants) and `GET /audits` (recent runs).
  - **Findings payload:** `GET /audits/{id}/findings` returns each finding with its cited records resolved server-side, so the UI never reads raw files.
  - **Concurrency:** one audit at a time; a second start gets 409.
  - **Progress:** per-control state (queued → running → done / error) comes from the graph's own stream. The UI polls every second.
  - **Frontend:** `frontend/` is Next.js 16.4 (App Router, TypeScript). `lib/data/` is the only code that calls `fetch`, and a test enforces this. Showcase mode is a stub until Phase 6.
  - **Types:** `mockaudit schema` → `json-schema-to-typescript` → `frontend/lib/types.gen.ts`, and CI fails if they drift.
  - **No answer key in the live UI:** it shows finding ids such as `C2-timeliness`. "Open G1" in the Verify line means that finding.

Verify: start an audit in the browser → 12 cards finish → open G1 → the step list shows → approve → export Markdown.

### Phase 6: Showcase and ship (end of Milestone 2)
- [x] `mockaudit export-showcase <run_ids>` writes the showcase JSON (cited records only, not full exports), and it validates against the schemas.
- [x] A static export (`output: 'export'`, `basePath`, `generateStaticParams`) builds; the Pages site has no start button and shows recorded review decisions.
- [x] `.github/workflows/pages.yml` deploys on push to `main`. (First deploy green: https://github.com/chiragsingla25/mock-audit-agent/actions/runs/38997158658; live at https://chiragsingla25.github.io/mock-audit-agent/)
- [x] README: what it is, the diagram, evaluation results (including agent vs checks-only), cost, how to run locally, the roadmap, and the note on synthetic data and practitioner review.
- [x] A 2-minute video script is in `docs/video-script.md`.

Clarified 2026-10-17 (Phase 6 clarify pass, ruled by Chirag):
- **Reviewed run:** a fresh base agent run (about US$0.03) that Chirag reviews in the local app, so the published decisions are a practitioner's. The eval runs are published alongside, marked unreviewed.
- **Comparison:** the showcase home lists every published run with its headline metrics in one table from eval.json (agent, skeptic-off view, checks-only, for base/a/b), and any run can be opened. There is no separate evaluation screen (still roadmap).
- **Fresh eval:** re-run `eval --all` (about US$0.15) so the README, eval.json and published runs all come from the shipped code.
- **Pages:** I enable Pages (source: GitHub Actions) on chiragsingla25/mock-audit-agent with one `gh api` call once pages.yml is ready.
- Defaults (builder, stated):
  - **Data shapes:** showcase JSON mirrors the API's shapes, so `lib/data/showcase.ts` reads static files where `live.ts` calls the API:
    - `public/data/index.json`: runs plus the eval summary;
    - `public/data/runs/<id>/audit.json`, `findings.json` (cited records only) and `report.json`.
  - **Validation:** `mockaudit export-showcase` validates everything it writes against Pydantic models, and CI re-validates the committed JSON (the step moved here from Phase 4).
  - **Static build:** `NEXT_PUBLIC_MODE=showcase` builds with `output: 'export'` and `basePath: '/mock-audit-agent'`. Query-string routes (Phase 5) mean no `generateStaticParams` is needed.
  - **No start button in showcase:** the Start screen becomes the run browser, and the Findings screen shows recorded decisions read-only.

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
- [phase 0] Tester swapped to `qwen/qwen3.5-flash-02-23` (allowed by §3) — ruled by Chirag 2026-10-15 — it completed 3/3 runs with no workaround. qwen3.8 needed reasoning off under `ToolStrategy` and hit an upstream 429. The cost is about the same (US$0.036 vs ≈0.041 per audit). qwen3.8 stays as `TESTER_FALLBACK_MODEL`, with reasoning off.
- [phase 1] RULING on G1 vs the "Friday 18:00 → Monday 09:00 is an exception" edge — raised by developer: the edge row would be a third late revocation not in G1's "5 and 9 days" — ruled by Chirag 2026-10-16: the weekend case replaces the 5-day row (G1 = 63 h and 9 days, still 2/18, high) — keeps the answer key at 10 gaps.
- [phase 1] RULING on "exactly 30 days passes and 31 fails" (handover §11 puts it in C8) — raised by developer: a 31-day C8 row would be a second SLA breach beside G8 — ruled by Chirag 2026-10-16: the 31-day fail is one of G9's C10 trainees, and C8 only gets the 30-day pass.
- [phase 1] research.md §4 says the observation period is 1 Jan–31 Dec 2026; the spec (locked) says 2025-10-01 to 2026-09-30 — doc drift — the generator uses the spec's period.
- [phase 1] The answer key needs the 7 severity rules, so `severity.py` was built in Phase 1 rather than Phase 2. It is covered by the answer-key test here, and Phase 2 adds its own threshold-edge unit tests.
- [phase 1] Check names in `controls.yaml` (`population_diff`, `revocation_delay`, `approval_before_grant`, `periodic_occurrence`, `set_mismatch`, `config_assert`, `author_ne_approver`, `unticketed_deploys`, `sla_days`, `required_link`, `days_after_event`, `date_in_period`) are now a contract that Phase 2 must implement. `required_link` is new (C9) and replaces architecture.md's `signoff_present`, which is unused because C3 sign-off is judgment-only. C12 is judgment-only too.
- [phase 1] C2 joins HR to Okta on `email`, not `employee_id`. A contractor conversion changes the Okta employeeNumber, so `email` is the stable key — data shape — params updated in controls.yaml.
- [phase 1] C7's "2 business days" is counted on UTC dates (Mon–Fri, no holidays), as stated in change_management.md 3.2 — unspecified before — fixed in the policy text.
- [phase 1] The generator lives at `backend/src/mockaudit/datagen/` (architecture.md had `backend/data_gen/`) so that `mockaudit gen` can import it from the installed package. The generated `data/ledgerly/{base,a,b}` (≈1 MB) are committed for browsing; tests regenerate into temp dirs.
- [phase 1] The first time-zone noise rows (09:00 Sydney + 1–3 h) landed on the same UTC date, so the noise wasn't there. `test_noise_is_present_and_not_a_gap` caught it — generator bug — fixed by terminating at 08:00 and revoking within 90 minutes.
- [phase 1 / review gate] The fresh-context review (`specs/reviews/2026-10-16-phase1-review.md`) returned FAIL on 2 criteria, both fixed — builder bugs — resolved as follows:
  - **Criterion 4:** the base "same-day suspension" row was suspended the next day. It now terminates at 13:00 local and is suspended 1–3 h later (same day in both local time and UTC), and the test checks for the same date.
  - **Criterion 6:** variant b re-used base's G3 record (UAR-2026Q3). Variants now draw G3/G4 quarters from those other than base's, and the test's G3 exemption is removed.
  - **Also fixed from the review's notes:** G1 `hours` are computed in UTC (Sydney wall-clock subtraction ignored DST); the Q3 sign-off noise is split into C3 (UAR) and C5 (PAR) entries; a reversed `period` now names the field; YAML syntax errors are wrapped in `ControlSpecError`.
  - **Check:** a seed sweep (1–60 × base/a/b, 180 datasets) passes every gap/trap query.
- [phase 1 / review gate] C10 new-hire training is scoped to `worker_type: employee` (recipe `where` param and policy 2.1 text) — the review found 2 contractors per variant hired in the period with no new-hire course, which a literal C10 check would raise as 2 unlisted exceptions — builder decision, open for Chirag to overrule (the alternative is to plant contractor training rows).
- [phase 1 → phase 2] The C8 30-day edge row is 30 days by calendar date but 30 d 6 h elapsed. Phase 2's `sla_days` must count calendar dates (policy 2.2), or it will flag that row.
- [phase 2] Base checks-only result (`runs/checks-base-…`): recall 8/10 (code 8/8), precision 8/10, clean-control accuracy 2/4, citation validity 28/28, severity agreement 8/8, traps raised 4/4. Variants a and b: recall 6/7 each, precision 75% and 67%. b's extra miss is C2 timeliness, which only the T1 trap triggers.
- [phase 2] Check params in controls.yaml were reshaped to what the checks read: `left_where`/`right_where`/`require_in` for `population_diff`, plus the `join` used by `sla_days`. Two named filters, `terminated_in_period` and `employed_throughout`, were added to the shared `where` matcher. C2 completeness now includes contractors, so the never-provisioned X3001 gets its note (handover §11) — recipe/data contract — datasets regenerated, and Phase 1 tests still pass.
- [phase 2] YAML 1.1 parses a key named `on` as boolean `True`, which broke the first `sla_days` join (`KeyError: 'on'`) — library quirk — renamed to `link_field`. Avoid `on`/`yes`/`no` as keys in controls.yaml.
- [phase 2] `TestStep.gap_type` (new field, default `operating`) and `ControlResult.candidates`/`dropped_citations` were added to the schemas. Findings need a type without an LLM, and citation validity counts dropped citations — interface addition, recorded for Phase 3's `TesterOutput`.
- [phase 2] `CHECKS` sits in a single `checks.py` (architecture.md sketched a `checks/` package). Twelve functions in one plain dict didn't justify a package — kept simple per CLAUDE.md.
- [phase 3] LangGraph 1.2.15's `add_node(..., error_handler=)` works for one task, but with parallel `Send` tasks the first exception is re-raised and fails the whole run. A scratch repro confirmed this in both sync and async, with and without `timeout=` — library gap — the `control` node therefore awaits the control subgraph inside `asyncio.wait_for` + `try/except` (as the proposal planned for timeouts) and returns `status: error` for that control only. Node `timeout=` also needs async execution, so the graph runs via `ainvoke`.
- [phase 3] `run --checks-only` now goes through the same graph (mode `checks_only`: the tester becomes a code node that raises every candidate, and the skeptic is skipped), as proposal §4 describes. The Phase 2 standalone runner was removed and `findings_from_candidates` kept. Phase 2's "no LLM" test now forbids importing LLM clients (`langchain_openrouter`, `openrouter`, `openai`, `mockaudit.llm`, `mockaudit.agents`) instead of all of LangChain/LangGraph — test scope adjusted to the graph-based design.
- [phase 3] Judgment-only steps gained `params: {source, prefix}` in controls.yaml so `sample` knows which artifacts to show (C3: UAR, C5: PAR, C12: restore_tests). `ControlResult` gained `tested_counts`, `samples`, `cost_usd` and `tokens`; `RunConfig` gained `controls` (a subset, for tests and debugging) — interface additions.
- [phase 3] Raised candidates that the tester decides on but never writes up still become findings, with templated code text ("raised by default"). Undecided candidates count as raised — builder default, so an LLM omission can't silently drop an exception.
- [phase 3] Revise re-entry passes the prior candidates, tested counts and samples in the `Send` payload, rather than re-running `population_check` / `run_checks`. The control subgraph's conditional `START` routes to `tester` when `revise` is set.
- [phase 3] First real base run `audit-base-20261016T091755120` (agent, review skip): recall 10/10, precision 10/10, clean controls 4/4, all 4 traps dismissed by the tester, citation validity 25/25, severity agreement 10/10. It cost US$0.031 (114,785 tokens, 31 LLM calls), and the trace is in LangSmith. The skeptic produced no revise verdicts, so the revise round is evidenced by stub tests (criterion 3 allows this).
- [phase 3] The C6 skeptic call used its whole 6,000-token budget on reasoning (6,000 reasoning tokens) and returned no tool call, so C6-segregation is `unresolved` in that run. The graph handled it as designed — model behaviour: DeepSeek reasons at length over a 320-PR population even at `effort: low` — **open for Chirag**: give the skeptic a reasoning budget (OpenRouter `reasoning.max_tokens`, e.g. 3,000) instead of `effort: low`, so the answer always has room, or accept occasional unresolved findings.
- [phase 3 / review gate] The fresh-context review (`specs/reviews/2026-10-16-phase3-review.md`) returned FAIL on criterion 5 and on one clarified rule, both in the revise round (which the real run never reached) — builder bugs — fixed with regression tests:
  - **Criterion 5:** a control that errored during revise returned nothing, so its stale draft could be re-reviewed and kept, and the error went unrecorded. Now the revised drafts become `unresolved` with a "revision failed" step, and the control's notes record the error.
  - **Clarified revise rule:** a revised finding whose items the tester dismissed stayed kept. It is now `dismissed`.
  - **Review note 1:** a tester finding whose citations were all invalid lost its raised exceptions. Tester findings now also carry their covered candidates' code-verified citations.
  - **Bug found while testing these fixes:** the severity node deleted every `rule`-kind reasoning step. It now replaces only earlier severity steps.
  - **Smaller notes, all fixed:** spend totals survive a resume (Spend reloads its run's lines); an edited `review_request.json` isn't overwritten, and reviewer notes are saved to `review_decisions.json` and shown in the report; the coverage table says "no exceptions found", never a bare "pass"; a skeptic error is labelled "the review could not complete"; `mockaudit review` on a checks-only run needs no model env vars.
- [phase 3 / review gate] `RetryPolicy` is now used as CLAUDE.md lists it: the `tester` node retries once on transient provider errors (429/5xx/network, matched by class name). Phase 0 saw an upstream 429. Schema failures and the spend cap are not retried.
- [phase 3 → 4] RULING on the skeptic's reasoning limit — Chirag first chose `reasoning.max_tokens: 3000`, but the OpenRouter SDK behind `ChatOpenRouter` drops it: the chat request type has only `effort`/`summary`, so the SDK sent `reasoning: {}`, and a C6 check run had reasoning silently off (`audit-base-20261016T094943841`) — library gap, the same family as the phase 0 `enabled: false` drop — re-ruled by Chirag 2026-10-16: skeptic `effort: minimal`, total `max_tokens` 12,000 (was low / 6,000). Verified on a real C6 run: the request body carried `{effort: minimal}`, and the skeptic used 901 reasoning tokens and answered `keep` (was unresolved). The tester is unchanged (`low`).
- [phase 4] Real `eval --all` (`runs/eval-20261016T101938Z`, re-scored with the fixed skeptic-off view): every target met.
  - **Agent, base run 1:** recall 10/10, precision 10/10, clean controls 4/4, citations 25/25, severity 10/10.
  - **Variants a and b:** 7/7 each, with clean controls 6/6.
  - **Stability:** 93% (pairs 90/100/90%; recall per run 100/90/100%).
  - **Checks-only:** recall 80%/86%/86%, precision 80%/75%/67%, all 4 traps raised in every variant.
  - **Cost:** US$0.032 and about 129k tokens per audit. Evaluation total US$0.16 of the US$2.00 cap.
- [phase 4] The skeptic added no precision on this data, and cost one true positive. In base run 2 it sent C3-signoff (G3) for revision, arguing the Q3 review might still be inside its 10-business-day window (deadline 2026-10-14). The tester then dropped it, so recall fell to 9/10 (the skeptic-off view keeps 10/10). This is also the first real revise round on base (criterion 3) — **dataset gap, open for Chirag:** no artifact states when the evidence was collected, so the skeptic's objection is defensible.
- [phase 4] The C6 skeptic ran away again at `effort: minimal`: 12,000 reasoning tokens and no answer, in 1 of 4 base-family runs (other runs used 714–3,821) — `effort` doesn't bound DeepSeek on this finding — **open for Chirag.**
- [phase 4] Builder bug in my own default: the skeptic-off view excluded findings dropped after a skeptic-requested revision, which hid exactly the harm it measures. It now counts them. `mockaudit eval --rescore <eval_id>` rebuilds an evaluation from runs on disk with no LLM calls, and the real evaluation was re-scored that way.
- [phase 4 follow-up] RULING (Chirag 2026-10-16) on the two open items — fix both:
  - **G3:** the dataset now records evidence collected 2026-10-30 (`dataset.yaml`, the answer key and the review artifact headers), after every Q3 sign-off deadline. Code computes each sampled review's sign-off facts (quarter end, due date at 10 business days, signed date, `deadline_passed`, `signed_on_time`) and gives them to the tester and skeptic, so neither LLM counts business days.
  - **C6:** the skeptic call is `with_fallbacks([effort: none call])`, triggered when the `minimal` call (now capped at 6,000 tokens) returns no answer. The verdict records `answered_by`.
  - **Verified:** 3 real C3+C6 runs; G3 kept and C6 answered 3/3 (561–2,835 reasoning tokens).
- [phase 4 follow-up] A fresh eval (`eval-20261016T112051Z`) exposed a builder bug: revising a code-only (`judge: none`) finding sent the tester no items, so the finding was then marked "tester dismissed". G7 was lost this way in 3 of 5 runs. The skeptic's complaint was fair too: code conditions named only the first missing week — fixed:
  - revised steps pass all their items to the tester;
  - a revised finding is `dismissed` only if the tester saw its items, otherwise `unresolved`;
  - code conditions list every failing item.
- [phase 4 follow-up] Final Milestone 1 eval `eval-20261016T114336Z`: every target met.
  - **Base:** 10/10 recall and precision in all 3 runs.
  - **Stability:** 100%.
  - **Variant b:** 7/7.
  - **Variant a:** 6/7. G1 was missed because the C2 tester ended its loop without calling `TesterOutput`, so the control errored, correctly isolated and reported.
  - **Cost:** US$0.030 per audit; eval total US$0.15 of the US$2 cap. Project spend is US$0.55 of US$10.
  - **Skeptic fallback:** answered 11 of about 55 skeptic calls (the `minimal` call hit its 6,000-token cap). All were keeps, and the cost stays bounded.
- [phase 4 follow-up] A tester that ends without `TesterOutput` now raises `TesterNoAnswer`, which the tester node's `RetryPolicy` retries once (as with schema failures) — reliability fix — stub-tested. It's not re-verified with another paid eval; the variant a miss above predates it.
- [phase 5] Verify line done by hand in the built-in browser on a real agent audit (`audit-base-20261017T022850664`, US$0.023):
  - **API down:** Start showed the exact API-down message.
  - **Progress:** 12 cards progressed and the run paused for review.
  - **Findings:** opened C2-timeliness (G1); its 16-step list, cited rows and the two-round skeptic exchange all showed.
  - **Review:** approved 8 findings and dismissed C12; the graph resumed.
  - **Report:** showed exactly the 8 approved findings, with the reviewer note.
  - **Export:** Markdown export returned 200.
- [phase 5] Builder bugs found by that live run, all fixed with regression tests:
  - **(a) Revise write-up:** in a revise pass where the tester re-raised items but wrote no finding, the finding was marked dismissed. G7 was lost again this way. A revise pass now applies the same "raised by default" code finding, keeping the revised id.
  - **(b) Card states:** cards said "running" when a control was merely *scheduled* (LangGraph emits task-start at scheduling), and stayed "revising" after a revise pass. Now "running" comes from the control node body (`AuditContext.on_control`), and task-finish events are matched by task id.
  - **(c) Coverage label:** coverage said "no exceptions found" for a control whose finding was dismissed in review. It now says "exceptions dismissed in review", and judgment-only controls show their sample size as population.
- [phase 5] Routing uses query strings (`/audit?run=…`, `/findings?run=…`, `/report?run=…`) instead of dynamic `[id]` segments, so every route prerenders as static and Phase 6's export needs no per-run `generateStaticParams` — design simplification against the Phase 6 wording, recorded for Phase 6.
- [phase 5] Frontend tooling: create-next-app 16.4.2 pinned `@types/node@^20`. The latest `@vitejs/plugin-react` needs Vite 8, which Vitest 3 doesn't ship, and Next's build typecheck failed on the config. The fix was Vitest 5 + `@types/node@24`, matching Node 24 — dependency gap.
- [phase 5] API additions beyond spec §4: `GET /config` and `GET /audits`. Reviewer submissions are saved to `review_submitted.json` — interface additions.
- [phase 5] Not fixed (noted):
  - A finding's step list holds every tool call of its control's tester run, not only the calls about that finding.
  - In the live run the skeptic misquoted policy 4.3 ("excludes weekends"), though its verdict was correct.
  - Both are LLM/presentation quality issues for the roadmap.
- [phase 6] Fresh eval `eval-20261017T024416Z` (after all fixes), as quoted in the README: every agent run perfect (base 10/10 ×3, variants 7/7), clean controls clean, no traps raised, stability 100%, US$0.014 per audit, eval total US$0.07. Checks-only is unchanged.
- [phase 6] Chirag's human review of `audit-base-20261017T024924682`: 3 approved, 7 dismissed, no notes. Published as is at his explicit instruction. The showcase labels its scores as counting only approved findings. The first submit attempt never reached the API: no POST was logged, the pane was closed and the dev server stopped, so it was redone.
- [phase 6] Static export: the template's `cacheComponents` / `partialPrefetching` enable partial prerendering, which `output: 'export'` rejects ("PPR cannot be enabled in export mode") — framework constraint — they're now live-mode only.
- [phase 6] Thanks to Phase 5's query-string routes, no `generateStaticParams` was needed, which differs from this phase's wording — recorded in phase 5.
- [phase 6] Recorded review decisions are now stored as `{finding_id, decision, note}`. They used to carry the whole review-request row.
- [phase 6] All eval agent runs are published, the stability runs included, so every comparison row opens a run (the validator enforces this). Each run also ships `report.md` for the Markdown export.
- [phase 6] The root `.gitignore` entry `runs/` also matched `frontend/public/data/runs/`, so the per-run showcase JSON would never have been committed. Caught before committing; CI's `validate-showcase` would have failed on it too — scaffold bug — anchored to `/runs/`.
- [phase 6] Verify line checked on the live site: the home shows runs and the comparison with no start button, findings show step lists and cited records, and the reviewed run's report holds the 3 approved findings. No console errors.
- [verify] Release-qa, 2026-10-17. Reviews: `specs/reviews/2026-10-15-mock-audit-mvp-m1-r1.md` (Milestone 1: PASS, 30/30 criteria), `…-m2-r1.md` (Milestone 2: Phase 5 PASS, Phase 6 FAIL), `…-m2-r2.md` (Phase 6 re-check: PASS). One fix round.
- [verify] Spec-conformance gap, not recorded by the developer: the Phase 6 Clarified rule "eval runs published alongside, marked unreviewed" wasn't met. The site didn't mark them, and every report was headed "Approved findings", including runs nobody reviewed. Fixed in fe5a13d with a "not reviewed" label and badge, plus a neutral heading and caption.
- [verify] Fixed in the same round from review notes:
  - **Data loss risk:** `export-showcase` deleted its output folder before validating run ids, and only checked that the folder was named `data`, so `--out data` at the repo root would have deleted the datasets. It now validates first and only replaces `<frontend>/public/data`.
  - **False confidence:** untested controls now read "not tested", not "no exceptions found".
  - **Broken table:** multi-line errors no longer break the Markdown coverage table.
- [verify] Divergences from framework §6, accepted rather than failed, because project rules or the spec's roadmap decide them:
  - CI runs no LLM evals (CLAUDE.md: never call OpenRouter from CI). The CI regression gate is deterministic: checks-only scoring plus stub-LLM tests. Real evals are run by hand with `eval --all`.
  - There is no judge-LLM for write-up quality; spec §2 makes it roadmap.
  - LangSmith traces were not re-inspected by release-qa; the trace and the real revise round rest on recorded evidence.
- [verify] Open notes (not blocking, roadmap or backlog):
  - **CLI:** `mockaudit review` ignores decisions other than approve/dismiss; `review --run latest` on a paused run says "no runs yet"; `eval --rescore <unknown>` prints a traceback; `mockaudit serve` always loads `.env`.
  - **API:** `POST /review` accepts partial decisions, and undecided findings drop out of the report (the UI blocks this).
  - **Validation:** `controls.yaml` accepts unknown check names, an empty file, or fewer than 12 controls.
  - **Counts and data:** C2/C5 completeness `tested` counts differ from the answer key's (severity still agrees); a header-only HR roster gives C2 "no exceptions found".
  - **Frontend:** the API response types (`lib/api-types.ts`) are hand-written, not generated; no frontend unit test covers the new badge or heading.
  - **Showcase:** the human-reviewed run (recall 3/10, captioned) leads the home table.
- [verify] User-visible changes in Milestone 2:
  - **Local app:** the new local app (`mockaudit serve` plus the Next.js UI) with the exact API-down message; browser-started audits always pause for review; coverage wording reads "no exceptions found", "exceptions dismissed in review" or "not tested", never "pass".
  - **Public site:** the public showcase at https://chiragsingla25.github.io/mock-audit-agent/ (unreviewed runs labelled, reviewed run with recorded decisions, comparison table), and the README rewritten with eval results and cost.
  - **Commands:** new commands `serve`, `schema`, `export-showcase`, `validate-showcase` and `eval --rescore`.
  - **Behaviour fixes:** the skeptic falls back to a non-reasoning call when the first returns no answer; a tester with no structured answer is retried once; revised code-only findings are no longer dropped.
