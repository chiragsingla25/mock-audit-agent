VERDICT: FAIL

Milestone 2 release-qa, round 1. BASE 03b17b0, HEAD eb47132. Reviewer: fresh context. No OpenRouter, LangSmith or `.env` was used. The API was started through `create_app` directly, because `mockaudit serve` calls `load_env()`.

## Verdicts
Phase 5: PASS (with notes)
Phase 6: FAIL (one clarified rule is not met: the eval runs are not marked unreviewed)

## Test suite
- Backend: `cd backend && uv run pytest -q` gave **115 passed** (40.7 s). `uv run ruff check .` gave "All checks passed!"
- Frontend: `npm test` gave **4 files, 9 tests passed**. `npm run typecheck`, `npm run lint` and `npm run build` were all clean, with 5 static routes.
- Showcase build: `NEXT_PUBLIC_MODE=showcase NEXT_PUBLIC_BASE_PATH=/mock-audit-agent npm run build` succeeded. `out/` had asset hrefs under `/mock-audit-agent/`, and no HTML file contained "Start audit". I deleted `out/` afterwards.
- Type drift: I ran `mockaudit schema` and `json2ts` into a scratch dir and diffed against the committed `schema.json` and `lib/types.gen.ts`. They are identical.

## What a user sees
- **Start screen (live).** It has dataset, mode (Agent / Skeptic off / Checks only), read-only models, spend and caps, and Start audit. With the API down, the click shows exactly "Can't reach the local API. Start it with `uv run mockaudit serve`." in an alert (`start-screen.test.tsx`). The Start button is disabled while another audit is busy.
- **Progress, findings, review and report (live, checks-only through a real uvicorn server on a scratch runs dir).** `POST /audits {base, checks_only}` paused with all 12 controls `done`. `/findings` returned 10 findings with `cited[].record` resolved (for example, the AR-0031 row inline). After the review was submitted, `/report?format=md` starts with "_Readiness forecast from synthetic evidence. Not an audit opinion._". The coverage table says "no exceptions found", never "pass". There is no pass badge in `ReportScreen.tsx` or `report.md`.
- **Findings detail.** It shows condition, criteria, cause, effect, recommendation, severity with its rule, skeptic verdicts by round, a numbered step list and the cited rows inline. In the reviewed run, G1 (`C2-timeliness`) has 17 steps and cites E1055/OK-000099 and E1109/OK-000261 (219 h and 63 h).
- **Showcase home (live site).** `curl` on https://chiragsingla25.github.io/mock-audit-agent/ and on `/findings/`, `/report/`, `/audit/`, `data/index.json`, a run's `findings.json` and `report.md` all returned 200. The deployed `index.json` matches the committed one, apart from `generated`. The home page is `ShowcaseHome` (no start button), with a Published runs table and an Agent vs checks-only vs skeptic-off table. I could only check the client-rendered content through its source and data, not in a browser.
- **README vs evidence.**
  - Every number in the Results table matches `runs/eval-20261017T024416Z/eval.json`.
  - The cost figures match too: US$0.013814 and 110,205 tokens per audit, US$0.069 eval total.
  - The README's "one revise round, then keep" matches the verdicts: r2 has 1 revise and the rest are keeps.
  - "Under US$1" matches `spend.jsonl`, which totals US$0.66.
  - The reviewed run is 3 approved and 7 dismissed, as stated.
- **Video script vs reality.** All its claims check out:
  - 63 h Friday-to-Monday row: yes.
  - "Two terminated users": G1 is 2/18.
  - E1083 is in the reviewed run's Not raised list, and checks-only raises it.
  - "About a cent and a half": US$0.014.
  - "Rules-only found eight of ten and raised all four traps": yes.
- **Reads oddly.**
  - The unreviewed eval runs' report pages are headed "Approved findings (N)". See For the builder.
  - The human-reviewed run is the first row on the home page, at recall 3/10. It has a caption, but that is the first number a visitor sees.

## Phase 5 Local app
| Criterion | Result | Evidence |
|---|---|---|
| One data layer (`NEXT_PUBLIC_MODE=live\|showcase`); screens never call `fetch` | Met | `structure.test.ts › only lib/data calls fetch` scans `app/`, `components/` and `lib/` except `lib/data`. `lib/data/index.ts` picks live or showcase. A grep found no XMLHttpRequest, EventSource or axios. |
| TS types generated from the Pydantic JSON Schema | Met | `structure.test.ts › generated types…`, the CI step `npm run gen:types && git diff --exit-code`, and my scratch regeneration (no drift). See the Note on `api-types.ts`. |
| Submitting the review resumes the paused graph; report shows only approved findings | Met | `test_api.py::test_full_flow_start_progress_findings_review_report`: stub LLMs, approve 1 of 10, and the report holds only `C2-timeliness`. Also `test_graph.py::test_report_says_dismissed_in_review…`. |
| API down shows the exact message | Met | `start-screen.test.tsx` (renders StartScreen, clicks, asserts the alert text) and `data.test.ts` (TypeError mapped to `ApiUnreachableError`). |
| Clarified: browser audits use `review_mode: human` | Met | Hard-coded in `api.py start()`, and asserted by the `/audits` row in the full-flow test. |
| Clarified: one audit at a time (409) | Met | `test_second_start_while_running_is_409_and_findings_wait` |
| Clarified: findings payload resolves cited records server-side | Met | The full-flow test asserts `record is not None`, and my live call returned rows. |
| Clarified: progress from the graph stream, running only when the body starts | Met | `test_progress_marks_running_only_when_the_body_starts…` and the 409 test (it sees `running`). |
| Verify line (browser, real audit) | Met by owner/builder | The [phase 5] deviation records it on `audit-base-20261017T022850664`. I could not repeat it, because I can't make LLM calls and have no browser. The API path is covered by the tests above. |

Adversarial inputs:
- `variant: "zz"` and a non-JSON body both gave 422.
- `/audits/..%2F..%2Fetc/report` gave 404.
- `decision: "maybe"` gave 422.
- A review naming an unknown `finding_id` plus one real id was accepted (202). The run finished, and the report holds only that one finding. See Notes.

## Phase 6 Showcase and ship
| Criterion | Result | Evidence |
|---|---|---|
| `export-showcase` writes the showcase JSON with cited records only, and it validates | Met | `test_showcase.py::test_export_writes_index…`, `::test_showcase_contains_cited_records_only` (uncited HR rows are absent) and `::test_validation_catches_a_broken_file`. Re-exporting the 9 published runs from `runs/` into scratch gave files byte-identical to the committed `frontend/public/data` (except `index.generated`). `mockaudit validate-showcase` reported 37 files valid. |
| Static export builds; no start button; recorded review decisions shown | Met | The showcase build succeeded. `app/page.tsx` renders `ShowcaseHome` in showcase mode, and `showcase.test.ts` makes start and submit reject. `test_reviewed_run_carries_recorded_decisions` checks decisions in the data. In the committed findings for `audit-base-20261017T024924682`, all 10 findings carry a decision. Query-string routing without `generateStaticParams` is a ruled deviation. |
| `pages.yml` deploys on push to `main` | Met | The workflow uses checkout, build with `NEXT_PUBLIC_MODE=showcase` and the base path, `upload-pages-artifact` and `deploy-pages`. The live URL serves HTTP 200 and its data matches the repo. |
| README sections | Met | It covers what it is, the diagram, eval results (agent vs checks-only), cost, how to run locally, the roadmap, and the synthetic-data and practitioner-review note. The numbers match `eval.json` and `spend.jsonl`. |
| 2-minute video script | Met | `docs/video-script.md` runs 0:00–2:00, and its claims match the runs (above). |
| Clarified: "The eval runs are published alongside, **marked unreviewed**" | **Not met** | Nothing on the site says "unreviewed"; `grep -ri unreviewed frontend/components` returns nothing. The only signal is that the reviewed run has a badge. Worse, `ReportScreen.tsx` heads every report "Approved findings (N)", so the skip-mode eval runs (for example `audit-a-20261017T024647072-r1`, `review_mode: skip`, 7 findings) say their findings were approved when nobody reviewed them. |
| Clarified: home comparison table from eval.json, every run openable | Met | `ShowcaseHome` comparison rows link to runs. `validate_showcase` enforces that every eval row has a published run. |
| Verify line (push → Pages shows runs, findings with step lists, comparison) | Met (data level) | Live fetches as above. The rendering is client-side, so I relied on the source plus data. The builder recorded a browser check. |

Adversarial inputs:
- `export-showcase no-such-run --out <scratch>/data` **deleted the existing output folder first** (a planted `precious.txt` was gone), then failed with a raw `FileNotFoundError` traceback. See Notes.
- `export-showcase` with no args gives an argparse error.
- A paused run is refused (tested).

## Regression sweep
BASE 03b17b0, BASE worktree in a scratch dir (since removed). Touched paths:
- `graph.py`: the raised-by-default write-up now also runs in revise passes; the `on_control` callback; normalised decisions.
- `report.py`: the "dismissed in review" note and label; judgment-only `population_size`.
- `runner.py`: `ainvoke` replaced by `astream` plus `aget_state`; `load_state`.
- `schemas.py`: `write_json_schema`.
- `cli.py`: `serve`, `schema`, `export-showcase`, `validate-showcase`.

`evaluation.py`, `scoring.py` and `checks.py` are unchanged.

| Input | Old vs new |
|---|---|
| `run --checks-only --review skip` on base, a, b, compared on report.md, report.json, run.json, verdicts.json and every controls/*.json, with run ids and timestamps normalised | report.md is identical. The only difference is C12 `population_size` 0 → 1, in all three variants. |
| `eval --run <that run>` on each | Identical scores: base 8/10 recall and precision, 2/4 clean, 28/28 citations, traps 4/4. a and b match too. |
| Checks-only `--review human`, then `mockaudit review` with alternate approve/dismiss | Same 5 findings in the report. C6, C9 and C10 change from "no exceptions found" to "exceptions dismissed in review" and gain a note. C12 population changes 0 → 1. |

All the differences come from the owner-ruled [phase 5] deviation (c). There is no unruled regression. The new revise-pass write-up is limited to the revised steps, because `tester()` filters `cands` to `steps_to_redo`. It is covered by `test_revise_pass_without_a_write_up…`.

## For the builder (failing phases only)
**Phase 6: the eval runs aren't marked unreviewed, and their reports say "Approved findings".**
- **Reproduce:** open https://chiragsingla25.github.io/mock-audit-agent/report/?run=audit-a-20261017T024647072-r1. The heading reads "Approved findings (7)", but the run is `review_mode: skip`. On the home page, the unreviewed rows carry no marker.
- **Correct:**
  - Unreviewed runs say so where they are listed (for example an "unreviewed" badge or label from `RunEntry.reviewed` / `review_mode`).
  - Their report and findings pages say so too.
  - The report heading depends on `review_mode`, for example "Findings (unreviewed, N)" for skip and "Approved findings (N)" for human.
  - A Vitest or render test that pins this would be enough.

## Notes (never a reason to fail)
1. **`export-showcase` deletes before it validates.** `export_showcase_async` runs `rmtree(out_dir)` before checking any run id. A typo wipes `frontend/public/data` (recoverable from git). The only guard is that the folder is named `data`, so `--out data` from the repo root would delete `data/ledgerly`. I suggest resolving and validating all run ids first, writing to a temp dir and swapping it in, and printing a one-line error instead of a traceback. This one is worth fixing soon.
2. **The API accepts partial or unknown decisions.** `POST /review` accepts unknown `finding_id`s and partial decision sets. Undecided findings silently drop out of the report, while their controls still say "exceptions". The UI blocks partial submits, so only API or CLI users can hit this.
3. **`report.md` wording.** It says "1 finding(s) dismissed in review". In checks-only, C12's population shows 1 although its only step was "not tested".
4. **View shapes are hand-written in TypeScript.** `lib/api-types.ts` (Audit, AppConfig, FindingView, Report, ShowcaseIndex) is hand-written, although `showcase.py` already has Pydantic `AuditView`, `FindingsView`, `ReportView` and `ShowcaseIndex`. The criterion is met for the domain types. Adding these models to `write_json_schema` would let CI catch drift in the API shapes too.
5. **`mockaudit serve` always loads `.env`, even for checks-only use.** That's fine for users. Reviewers and CI have to bypass it.
6. **The live client reads only string `detail` from errors.** A 422 shows as "422 Unprocessable Entity". The UI's fixed choices make this unreachable in practice.
7. **Architecture rules hold.**
   - The API's `asyncio.create_task` only drives one graph invocation in the background, so there is no orchestration outside LangGraph.
   - There are no new LLM nodes, and severity stays code-only.
   - No test reaches OpenRouter: the API tests use `StubModels`, and the checks-only test asserts that no models are built.
8. **The human-reviewed run leads the home table at 3/10 recall.** That's correct and captioned, but consider ordering the eval agent run first, or adding a one-line explanation next to the number.
