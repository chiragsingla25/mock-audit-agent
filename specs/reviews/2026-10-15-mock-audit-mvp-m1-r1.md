VERDICT: PASS

Release-qa, Milestone 1 (Phases 0–4), round 1. Spec `specs/2026-10-15-mock-audit-mvp.md`. BASE 0bdd115, reviewed at HEAD eb47132. Reviewer: fresh context, 2026-10-17. No OpenRouter or LangSmith calls were made and `.env` was never loaded. Generated data and runs went to a scratch dir, which has been deleted.

## Verdicts
Phase 0: PASS (evidence only, not re-run)
Phase 1: PASS WITH NOTES
Phase 2: PASS WITH NOTES
Phase 3: PASS WITH NOTES
Phase 4: PASS WITH NOTES

## Test suite
`cd backend && uv run pytest -q && uv run ruff check .` gave **115 passed** in 40 s, and ruff reported "All checks passed!". CI (`gh run list --workflow ci.yml`): the last 5 pushes are green, including 38891182571 (the Phase 4 first run) and 38997263064 (HEAD).

## What a user sees
- `mockaudit gen --variant all --out <tmp>` run twice gives `diff -r` identical output, which is also identical to the committed `data/ledgerly/`. `--seed 7` is the same as base's default.
- `mockaudit run --checks-only --variant base` printed "10 findings in the report · cost US$0.0000 · 0 tokens · 0 LLM calls". Then `mockaudit eval --run latest` printed a metrics table: recall 8/10, code 8/8, precision 8/10, clean controls 2/4, citations 28/28, severity 8/8, traps raised 4/4, plus "Missed gaps: G3, G10 · unmatched findings: C1-approval, C9-pir". This matches the clarified expectations exactly.
- report.md is headed "Ledgerly SOC 2 readiness report" with "_Readiness forecast from synthetic evidence. Not an audit opinion._". Coverage says "exceptions" or "no exceptions found", never "pass", and there is no pass badge. The same holds for the real agent run `runs/audit-base-20261017T024416974-r1/report.md`: 12 control files, report.md/json, verdicts.json, 10 findings, US$0.0147, 32 LLM calls.
- `runs/eval-20261017T024416Z/eval.md` reads well. It has a targets table with met/missed, every run with its skeptic-off view, agent vs skeptic-off vs checks-only per variant, stability with pairs, and cost per audit. One small oddity: the target column reads "≥ 100%" for clean controls and citations.
- Things a user would notice (Notes 1–2): in checks-only, C12's only step is not tested, yet its status reads "no exceptions found". The C2-completeness and C5-completeness denominators (1 of 20, 1 of 30) differ from the answer key's `tested` (19, 8).

## Phase 0 MVP notebook (evidence only)
| Criterion | Result | Evidence |
|---|---|---|
| Runs top to bottom with real calls on the Mac | met | Spec result block, run `mvp-20261015T103418Z`. The notebook's saved outputs contain 0 error outputs, and `runs/mvp-…/bakeoff.jsonl` exists. |
| Per-model table (late, missing, trap, invented cites, tokens, US$) | met | Spec table. The notebook output contains rows like "late 2/2, missing 1/1, trap dismissed True, invented 0 …". |
| Reasoning step list printed | met | Notebook output "qwen/qwen3.8-flash \| 1. [check] …". |
| Projected US$/audit, stop if > 0.40 | met | Output "projected US$ per 12-control audit … 0.036". The 0.027/0.041 discrepancy for qwen3.8 is explained in Deviations. |
| Schema-failure retried once, shown | met | Output "retry: StructuredOutputValidationError". |

## Phase 1 Schemas and dataset
| Criterion | Result | Evidence |
|---|---|---|
| gen writes the layout, byte-identical twice | met | `test_gen_writes_layout_and_twice_is_byte_identical`, plus my `diff -r` of two `gen --variant all` runs (identical). |
| Key lists G1–G10 tagged, traps, clean C1/C4/C9/C11, severities by the 7 rules | met | `test_answer_key_lists_gaps_traps_clean_controls` and `test_severities_come_from_the_seven_rules` (the test recomputes `severity()` per gap, on all variants). I also read `severity.py` against architecture.md §6: they match rule for rule. |
| Documented query per gap and trap | met | `test_queries_find_every_gap_and_trap` (base, a, b) |
| Noise present | met | `test_noise_is_present_and_not_a_gap` (name format, AEST vs UTC, same-day suspend then delete, compliant emergency, late-in-week scan) |
| Domain-rule edges | met | `test_domain_rule_edges` (63 h exception; C8 30 d pass; C10 30 d pass and 31 d fail per ruling; Dec 15 → Jan 10 pass) |
| Variants A/B re-plant, keys match | met | `test_variants_replant_different_combinations` (7 gaps each, different combinations, different records) and the query test on a and b |
| Invalid controls.yaml names the control and field | met | `test_invalid_controls_yaml_names_control_and_field` |

Adversarial (script calling `load_controls` on mutated yaml):
- risk "extreme" gives "control C4: field 'risk': …";
- a duplicate id gives "control C1: field 'control_id': duplicate id";
- a bad gap_type names `test_recipe.0.gap_type`;
- an unknown `check` name, an empty list and an 11-control file all load with no error (Note 8).

## Phase 2 Checks and scoring
| Criterion | Result | Evidence |
|---|---|---|
| Each check has unit tests with both threshold edges | met | 22 tests in `test_checks.py`. The registry test asserts every recipe check is in `CHECKS` (12). The edges tested include 24.0 h vs 24.1 h, the Sydney DST/UTC case, and 30/31 days. |
| checks-only raises every candidate with citations, no LLM | met | `test_checks_only_writes_12_results_with_cited_candidates` and `test_checks_only_makes_no_llm_calls` (fresh interpreter, no LLM modules imported), plus my run (0 LLM calls) |
| Scorer reports the 5 metrics and matches on control plus ≥ 1 record | met | `test_scorer_matches_on_control_and_one_cited_record` (includes a right-record, wrong-control negative), `test_scorer_counts_dropped_and_unknown_citations_against_validity` |
| Checks-only on base finds every code gap and raises every trap | met | `test_checks_only_finds_every_code_gap_and_raises_every_trap` (base, a, b), plus my run: 8/8 code, traps 4/4 |
| Nonexistent citation dropped and logged | met | `test_citation_check_drops_and_logs_nonexistent_record` (asserts the log text) |

Adversarial (copy of base with a header-only `hr_roster.csv` and `scanner_runs.csv`, then `run --checks-only`):
- The run completed and isolated the failure.
- C2 read "no exceptions found" with 0 tested and no note (Note 3).
- C8 errored with a raw Pydantic `ValidationError` (a missing-week candidate has no neighbouring scan to cite). The multi-line message broke the Markdown coverage table (Note 4).

## Phase 3 Audit graph
| Criterion | Result | Evidence |
|---|---|---|
| `run --review skip` gives 12 result files and a report | met | `test_review_skip_writes_12_results_and_report` (stub chat models inside the real `create_agent` graph), plus the real run folder `audit-base-20261017T024416974-r1` |
| Merge by finding_id; a revised control keeps kept findings | met | `test_merge_findings_reducer_never_lets_a_draft_overwrite_a_reviewed_finding`, `test_revise_round_reenters_tester_and_keeps_kept_findings` (compares the kept finding to a baseline, and checks the unrequested rewrite is ignored) |
| ≥ 1 revise round (LangSmith or stub) | met | The same revise test (verdicts `#r0` revise, `#r1` keep). Spec Deviations [phase 4] records a real revise round in base run 2 (not checked in LangSmith by me). |
| Nothing to review goes straight to severity | met | `test_nothing_to_review_goes_straight_to_severity` (C4/C11: no skeptic node, no LLM call) |
| Exception or timeout errors only that control | met | `test_exception_in_one_control_errors_only_that_control`, `test_timeout_in_one_control_errors_only_that_control`, `test_control_error_during_revise_leaves_finding_unresolved_and_recorded` |
| Spend over the cap stops LLM calls, rest `spend_cap` | met | `test_spend_cap_stops_llm_calls_and_marks_remaining_controls` |
| Reasoning steps on every finding and dismissal | met | `test_every_finding_and_dismissal_has_reasoning_steps` |
| `--review human` pauses; resume reports only approved | met | `test_human_review_pauses_and_resume_reports_only_approved`, plus my checks-only human run resumed via `mockaudit review`: 2 approved gave a report with exactly those 2 |

Architecture rules: one `StateGraph` using `Send` (dispatch, skeptic fan-out, revise re-entry), `Annotated` reducers (`merge_findings`), a conditional `START` in the control subgraph, `interrupt` in `human_review`, `RetryPolicy` on `tester`, and `AsyncSqliteSaver`. The tester is `create_agent` + `ToolStrategy(TesterOutput)` with exactly get_record/read_policy/ask_owner. Severity is code only. The `asyncio.wait_for` inside the `control` node is the recorded [phase 3] deviation; there is no hand-written runner.

Adversarial:
- Decisions all set to "maybe": accepted silently. 0 findings in the report, but the findings stay `kept` and coverage still says "exceptions" (Note 5).
- `mockaudit review --run latest` on a paused run: "no runs yet … start one with `mockaudit run --checks-only`" (Note 6).

## Phase 4 Evaluation and CI
| Criterion | Result | Evidence |
|---|---|---|
| eval --all runs agent base/a/b, skeptic-off, checks-only, 3 stability; writes eval.json and a table | met | `test_eval_all_runs_agent_variants_stability_checks_only_and_skeptic_off`, `test_skeptic_off_is_derived_with_no_extra_llm_calls`, plus the real `runs/eval-20261017T024416Z/{eval.json,eval.md}` |
| Reports all metrics, stability, the comparisons, US$ and tokens | met | `test_eval_reports_all_metrics_comparisons_stability_and_cost`, plus the real eval.md |
| Total eval spend ≤ US$2.00 (from spend.jsonl) | met | I summed `runs/spend.jsonl` over the 5 eval agent run ids: US$0.069068, equal to eval.json `eval_total_usd`. The cap logic is covered by `test_eval_spend_cap_skips_runs_that_would_exceed_it`. |
| ci.yml: ruff + pytest + showcase validation, no secrets, no LLM | met | `test_ci_workflow_runs_lint_and_tests_without_secrets`, plus my read of ci.yml (ruff, pytest, validate-showcase, `LANGSMITH_TRACING=false`, no `secrets.`), plus green runs |
| Targets reported honestly | met | `test_missed_targets_are_shown_not_hidden`. In real history, a 6/7 miss on variant a and a skeptic cost of 1 TP were recorded in the spec. |

Adversarial:
- Copied the real eval and its 8 run folders to scratch and ran `eval --rescore eval-20261017T024416Z` with HEAD code. Every eval.json key was identical to the recorded one.
- `eval --rescore nope` gives a Python traceback (Note 7).
- `eval --run nope` gives a clean message.

## Regression sweep
BASE 0bdd115 has no backend code (only the scaffold and the notebook), so Milestone 1 is a new project against BASE. Since later fixes are in scope, I also swept Milestone 2's changes to Milestone 1 code (03b17b0..HEAD: `graph.py` tester write-up in revise and `on_control`, `human_review` decision shape, `report.py` coverage status and population_size, `runner.py` streaming and resume) using a worktree at 03b17b0.
- **checks-only base/a/b, old vs new:** eval tables, eval.json, verdicts.json, report.md and every control file are identical except `C12.population_size` 0 → 1. That is the recorded [phase 5](c) change.
- **checks-only `--review human` + `mockaudit review`** (mixed approve/dismiss/blank decisions): the same 4 findings in both reports. The only differences are recorded ones: "exceptions dismissed in review" with a note ([phase 5](c)), and `review_decisions.json` reduced to `{finding_id, decision, note}` ([phase 6]).
- **Old test suite on new code:** the 03b17b0 test files run against HEAD gave 99 passed and 1 failed. The failure is `test_ci_workflow…` resolving `.github` relative to the scratch copy's location, not a code regression.
- No unrecorded regressions. Worktree and scratch removed.

## Notes (never a reason to fail)
1. In checks-only, a control whose steps are all `not_tested` (C12) shows status "no exceptions found". The Not-tested column says why, but the status could read as clean. Consider "not tested".
2. The C2-completeness denominator (20) and C5-completeness denominator (30) differ from the answer key's `tested` (19, 8). Severity agrees today because rule 2 ignores counts, but a rate-based rule would diverge.
3. An empty population (header-only HR roster) gives C2 "no exceptions found" with 0 tested and no note.
4. A control error message is written raw and multi-line into the Markdown coverage table, which breaks the table. Zero scans hit this, via a candidate with no citation.
5. `mockaudit review` silently ignores decision values other than approve/dismiss. Those findings stay `kept`, are left out of the report, and coverage still says "exceptions". A warning or rejection would be clearer.
6. A paused run isn't `LATEST`, so `review --run latest` gives a misleading "no runs yet" message. The pause hint prints the explicit id, so this is minor.
7. `eval --rescore <unknown id>` raises a `FileNotFoundError` traceback rather than a message.
8. `load_controls` accepts an unknown check name, an empty file and a file with fewer than 12 controls. These would surface later as a control error or as missing controls.
9. eval.md shows "≥ 100%" as a target, which reads oddly; "100%" or "all" would be clearer.
10. The spend guard is checked before each call, so a run can overshoot the cap by one call (the stub test reaches 1.2 on a 1.0 cap). This is as designed, and with real costs of about US$0.001 per call the overshoot is negligible.
11. I did not verify the LangSmith trace (Phase 3 Verify line) or the real revise round in LangSmith. I relied on the spec's recorded run evidence and the stub test, as the criterion allows.
