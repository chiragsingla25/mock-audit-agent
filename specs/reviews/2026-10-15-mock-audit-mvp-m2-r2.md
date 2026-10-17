VERDICT: PASS

Milestone 2 release-qa, round 2 (re-check of Phase 6 only). BASE eb47132, HEAD fe5a13d. Scope: the fix diff `git diff eb47132 HEAD`. No OpenRouter, LangSmith or `.env` was used.

## Verdicts
Phase 6: PASS (the round 1 failure, eval runs not marked unreviewed, is resolved)

## Test suite
- Backend: `cd backend && uv run pytest -q` gave **117 passed** (115 in r1, plus 2 new tests). `uv run ruff check .` gave "All checks passed!"
- Frontend: `npm test` gave **4 files, 9 tests passed**. `npm run typecheck` and `npm run lint` were clean.
- Showcase build: `NEXT_PUBLIC_MODE=showcase NEXT_PUBLIC_BASE_PATH=/mock-audit-agent npm run build` succeeded with 5 static routes. The bundle contains "not reviewed by a person" and the caption "Not reviewed by a person: these are the findings the agent kept (evaluation run)." I deleted `out/` afterwards, and `git status` is clean.

## What a user sees
- **Home, runs table (`ShowcaseHome.tsx`).**
  - Each unreviewed run now shows a "not reviewed by a person" badge.
  - The reviewed run keeps its green "review decisions recorded" badge.
  - Labels in `index.json` now end in "· not reviewed" for all 8 skip-mode runs (for example, "Ledgerly base · agent · not reviewed · stability run 2"). The single human run reads "Ledgerly base · agent · human-reviewed".
- **Report page (`ReportScreen.tsx`).**
  - The heading is "Approved findings (N)" only when `review_mode === "human"`. Otherwise it is "Findings (N)", followed by the not-reviewed caption.
  - Coverage reads "not tested" when a pass row has no tested steps.
- **Committed `report.md` files.**
  - The 8 eval runs read `## Findings (N)` followed by the caption.
  - The reviewed run `audit-base-20261017T024924682` reads `## Approved findings (3)`, with no caption.
  - In the 3 checks-only runs, C12 reads `not tested | — | restore_test (judgment-only step (checks-only mode))`.
- **Committed data matches a fresh export.** I re-exported the 9 published runs (with `--eval eval-20261017T024416Z`) into a scratch `.../fe/public/data`. The result is "37 files, all valid", and it is byte-identical to the committed `frontend/public/data` apart from `index.generated`.

## Phase 6 Showcase and ship (re-check)
| Criterion | Result | Evidence |
|---|---|---|
| Clarified: eval runs published alongside, **marked unreviewed** | Met | `test_showcase.py::test_unreviewed_runs_are_marked_and_their_reports_do_not_claim_approval` checks labels plus `report.md` heading and caption for every run, reviewed or not. For the UI I relied on the source and the build bundle (above), because no frontend test covers the badge or heading. |
| Reviewed run still reads "Approved findings" | Met | The same test (reviewed branch), plus the committed `report.md`, plus `ReportScreen.tsx` line 61. Live-mode audits are always `review_mode: human`, so the live report heading is unchanged. |
| Note fix: export validates before deleting | Met | `test_a_bad_run_id_deletes_nothing`. Checked by hand on a scratch `public/data` holding `precious.txt`: `export-showcase no-such-run` printed "export-showcase: no run 'no-such-run' in .../runs" with rc=1, and the file survived. `--eval no-such-eval` gave "no evaluation 'no-such-eval'" with rc=1, and the file survived. Neither case printed a traceback. |
| Note fix: refuses `--out data` | Met | `test_export_refuses_unfinished_runs_and_odd_output_folders` (both `public` and `data`). By hand, from a scratch dir holding `data/p.txt`: `--out data` printed "refusing to replace data: the showcase output folder must be <frontend>/public/data" with rc=1, and `p.txt` survived. |
| Note fix: untested controls read "not tested" | Met | The committed checks-only reports (C12), my regenerated output, and `coverageLabel(status, notes, tested)` in `ReportScreen.tsx`. |

Adversarial inputs: a missing run id, a missing eval id, and a bare `--out data`, all covered above. Each failed cleanly and deleted nothing.

## Regression sweep
BASE eb47132, in a worktree in a mktemp dir (removed afterwards).

Touched paths:
- `report.render_md`: the heading and caption by `review_mode`, "not tested", and one-line errors.
- `showcase.export_showcase_async`: the output-path rule, pre-validation, re-rendered `report.md`, and labels.
- `cli` export-showcase: clean error exit.
- `ReportScreen.coverageLabel` and the heading.
- The `ShowcaseHome` badge.

Comparison: I rendered every `runs/*/report.json` in the local runs dir through BASE and HEAD `render_md`, then diffed the outputs. The only differences are:
- 38 skip-mode reports gain the caption line;
- 12 checks-only C12 rows change from "no exceptions found" to "not tested";
- 2 human runs change from "## Findings (N)" to "## Approved findings (N)".

All of these are intended. No other line changed, and the error-flattening path was not triggered by any existing data. The `results` argument of `render_md` is now optional and unused, and `write_run` still passes it, so nothing breaks.

## Notes (never a reason to fail)
- The caption says "the findings **the agent** kept (evaluation run)" on checks-only runs too, where no agent ran. It also says "(evaluation run)" on any manual `mockaudit run --review skip` run, not just eval runs. Wording like "Not reviewed by a person (review skipped)." would be accurate in every case.
- No frontend unit test covers the new badge, heading or "not tested" label. Only the backend `report.md` path and `index.json` labels are tested.
- The empty-state text "No findings were approved." still appears on unreviewed runs that have zero findings. No published run hits this case.
