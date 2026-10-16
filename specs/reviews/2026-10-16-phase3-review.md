VERDICT: FAIL

Reviewer: fresh-context review of Phase 3 "Audit graph" (review gate). BASE c5b3588, HEAD 851dd05. No code or data edited; no OpenRouter/LangSmith calls; scratch worktree and runs removed.

## Verdicts
Phase 3: FAIL. 7 of 8 criteria met. Criterion 5 fails on the revise-round path, and one clarified rule (revise round: "same finding_id, or is dismissed") is not met.

| # | Criterion | Verdict |
|---|---|---|
| 1 | `--review skip` → 12 control files + report | PASS |
| 2 | Merge by `finding_id`; revised control keeps kept findings unchanged | PASS |
| 3 | ≥ 1 revise round (LangSmith or stub) | PASS (stub) |
| 4 | Nothing to review → straight to severity | PASS |
| 5 | Exception/timeout in one control → `status: error` for that control only | **FAIL** (revise round) |
| 6 | Spend over cap stops LLM calls, remaining controls `error: spend_cap` | PASS WITH NOTES |
| 7 | Every finding and dismissal carries reasoning steps | PASS |
| 8 | `--review human` pauses; resume → only approved findings | PASS WITH NOTES |
| C | Clarified rule: a revised finding "comes back with the same `finding_id`, or is dismissed" | **FAIL** |

## Test suite
`cd backend && uv run pytest -q` → 74 passed in 9.7 s. `uv run ruff check .` → All checks passed.

## What a user sees
- Phase 3 Verify: I did not re-run it (agent mode calls OpenRouter). I read the existing real run `runs/audit-base-20261016T091755120/`. It has 12 `controls/*.json`, plus report.md, report.json, verdicts.json, run.json and eval.json. The totals are US$0.030926, 114,785 tokens and 31 calls. All 12 controls completed, with 10 findings in the report. The report says "Readiness forecast from synthetic evidence. Not an audit opinion." I can't check the LangSmith trace from here.
- Phase 2 Verify (`run --checks-only --variant base` then `eval --run latest`, with a temp `--runs-dir`) prints the same metrics table as BASE: recall 8/10, precision 8/10, clean 2/4, citations 28/28, severity 8/8, traps 4/4.
- Things in the report that read oddly:
  - The Coverage table shows a bare **`pass`** status for C1, C4, C9 and C11 (report.md lines 9/12/17/19, from report.py:67). That is close to the "no pass badge anywhere" rule (see Notes).
  - C6-segregation is labelled "**unresolved** (reviewer and tester disagree)". In fact the skeptic call failed (6,000 reasoning tokens, no tool call; the verdict is `error`), so nobody disagreed (report.py:73).

## Phase 3 Audit graph
| Criterion | Result | Evidence |
|---|---|---|
| 1 | PASS | `test_review_skip_writes_12_results_and_report` (stub, full graph via `run_audit`), and the real run dir above: 12 files, report present, every control status non-error |
| 2 | PASS | `test_merge_findings_reducer_never_lets_a_draft_overwrite_a_reviewed_finding` (reducer), `test_revise_round_reenters_tester_and_keeps_kept_findings`: kept C2-completeness and all C8 findings are byte-equal to the baseline, and the stub's unrequested "SHOULD NOT APPEAR" rewrite is ignored. Not vacuous: the stub really does try to rewrite a kept step. I traced every path. The reducer blocks draft→non-draft overwrites (graph.py:63-72). `tester_findings` skips non-revised steps (graph.py:189). Finalize drops code findings on revise (graph.py:266). `route_after_skeptic` and `severity_node` update only from code. The report reads state. |
| 3 | PASS | The same test asserts `verdicts["C2-timeliness#r0"]=="revise"`, `#r1=="keep"`, `revision_round==1` and the condition starts with "revised: ". The real run had no revise verdict (recorded deviation). |
| 4 | PASS | `test_nothing_to_review_goes_straight_to_severity`: streams node updates for C4+C11 and asserts no `skeptic_one`/`route_after_skeptic`, the order await_controls < severity < report, and zero LLM calls |
| 5 | **FAIL** | First pass: `test_exception_in_one_control_errors_only_that_control` and `test_timeout_in_one_control_errors_only_that_control` pass. **Revise round:** an exception in the control during revise gives no error status anywhere (see For the builder #1). |
| 6 | PASS WITH NOTES | `test_spend_cap_stops_llm_calls_and_marks_remaining_controls`: with cost 0.4/call, cap 1.0 and concurrency 1, exactly 3 calls are made (the stub log and spend.jsonl both have 3 lines), and the capped controls have `error` starting with `spend_cap`. The guard runs in `SpendCallback.on_chat_model_start` with `raise_error=True` (llm.py:59-65), before the model's `_agenerate`; the stub log proves the 4th call never reached the model. The cap is isolated per control by `control()` (graph.py:345-361). |
| 7 | PASS | `test_every_finding_and_dismissal_has_reasoning_steps`. Real run: every finding has check/tool/llm/rule (C3/C12 llm/tool/rule; C8-weekly_scan check/llm/rule), and every dismissal has check/llm/tool. |
| 8 | PASS WITH NOTES | `test_human_review_pauses_and_resume_reports_only_approved`. I also resumed from a **fresh Python process** with `resume_audit(run_dir, decisions, models)`, using only config.json and checkpoints.db. The report listed exactly the 2 approved ids. The context is rebuilt from config.json (runner.py:51-59). |
| C | **FAIL** | See For the builder #2 |

Architecture rules:
- One `StateGraph` with `Send` fan-out (graph.py:336, 372-379, 428-446), reducers (75-84), a conditional `START` in the control subgraph (313), `interrupt` (477) and `max_concurrency` (runner.py:33).
- There are exactly two LLM call sites: `tester` (create_agent + ToolStrategy) and `skeptic_one`.
- Counts come from code: candidate ids for check steps (196), and cited∩sample for judgment steps (198). Severity is always `severity()` (205, 457), never LLM output. An LLM finding that says "999 of 1000" in its condition still gets `exceptions` from code.
- **`asyncio.wait_for` + `try/except` in `control`** (graph.py:348-361) is a single awaited call with a timeout and an error mapping. It has no loop, no scheduling and no retry, and fan-out and concurrency stay with `Send`/`max_concurrency`. In my judgement it stays within the "no hand-written runner/retry/orchestrator" rule.
- `RetryPolicy` (listed in CLAUDE.md) is not used anywhere (see Notes).

Adversarial inputs tried (stub models, temp dirs):
- **Tester cites another control's source / only bogus ids:** C2 timeliness finding citing `github_prs/PR-1230`, plus a duplicate citing `hr_roster/NOPE-1`. Both were dropped and logged (`dropped_citations` lists both). The index is per-control (evidence.py:89). Side effect: the real exceptions vanished (Notes #1).
- **Duplicate finding ids:** the second finding for a step becomes `C2-timeliness-2` (graph.py:203-204). Nothing collides with a kept id, and the reducer would block it anyway.
- **Skeptic raises:** verdict `error`, and the finding becomes `unresolved`. OK, but it gets the misleading label above.
- **Revise round, control raises:** FAIL #1. **Revise round, tester dismisses:** FAIL #2.
- **Human resume in a fresh process:** works. The cost totals and the reviewer's notes are lost (Notes #2, #3).

## Regression sweep
BASE c5b3588 (Phase 2). Touched paths:
- `run_control_checks` (new `only=` filter)
- checks-only now goes through the graph (`population_check`/`run_checks`/`tester` code path/`finalize`)
- `findings_from_candidates`
- `controls.yaml` (params on 3 judgment steps)
- `ControlResult`/`RunConfig` fields
- CLI `run`
- scorer input

Compared `mockaudit run --checks-only` at BASE (git worktree) and HEAD for variants base, a and b, then diffed every `controls/*.json` field by field:
- **Findings:** for every control, the ids, test_step, gap_type, exceptions, tested, condition, criteria, citations, severity, rule and status are identical. The only difference is order: C8 findings are now sorted by id. In the reasoning, the rule step text now reads `severity rule 6: sla_breach, 2/9, moderate-risk control → moderate` instead of `severity rule 6 → moderate`.
- **C5 check_results:** different order (population step first), same multiset.
- **New fields** `tested_counts`, `samples`, `cost_usd` and `tokens`. **`sample` is now filled in checks-only** for C3/C5/C12 (e.g. C3 lists 4 UARs), although those steps are reported `not_tested` (Notes).
- **New artifacts:** checks-only runs now also write report.md, report.json, verdicts.json, config.json and checkpoints.db.
- **Eval on base:** the metrics table is identical to BASE (above).

No behavioural regression. Worktree removed.

## For the builder (failing phases only)
1. **A control that errors in the revise round is silently swallowed.** This is criterion 5. graph.py:359-360 returns `{}`, and its comment says "route_after_skeptic marks them unresolved". That doesn't happen. The old draft goes back through `await_controls` → `to_skeptic` (372-379) and is re-reviewed at round 1. If the skeptic says keep, it ends **kept**. The control result keeps `status: exceptions, error: null`, and the error appears nowhere in controls/*.json, verdicts.json or report.
   Repro: tester stub that raises when `REVISE_JSON` is in the message; skeptic `revise` for C2-timeliness at r0, else keep; `controls=["C2"]`. Result: `C2 status=exceptions error=None`, `C2-timeliness kept`, verdict keys `[#r0, #r1]`.
   Correct: the error is recorded for that control, e.g. `status: error` or an error field/reasoning step on the affected findings. Either the revised findings become `unresolved` as the comment and the clarified rule ("anything still marked revise after 1 round becomes unresolved") say, or the spec is updated to say otherwise.
2. **A revised finding whose candidates the tester dismisses is not removed.** This is the clarified rule "each comes back with the same finding_id, or is dismissed". In the revise round, finalize returns no finding for that id (graph.py:284-286). The stale draft stays in state, is re-reviewed and kept, while the same candidates are also written as dismissals.
   Repro: tester stub that, on revise, dismisses every candidate and writes no findings; same skeptic script; `controls=["C2"]`. Result: `C2-timeliness kept, exceptions 2/18`, *and* dismissals `C2-timeliness-E1055`, `C2-timeliness-E1109`. The report shows a high finding whose records are listed as dismissed.
   Correct: when every candidate of a revised finding is dismissed (or the revised write-up is dropped), the finding leaves the report: status `dismissed`/`rejected`, or `unresolved` if the write-up was dropped. It must not be kept unchanged. A stub test should cover it.

## Objections
None.

## Notes (never a reason to fail)
1. **(Possibly blocking; owner to decide) A finding dropped by the citation check takes its raised exceptions with it.** `tester_findings` marks candidates `covered` (graph.py:195) before `finalize` runs the citation check (268-272), and the "raised by default" fallback (211-217) only applies to uncovered candidates. If the LLM writes a finding for real exceptions but cites a wrong record, the finding is dropped and the exceptions appear nowhere: not as a finding, not as a dismissal.
   Repro: C2 tester finding with candidate_ids E1055/E1109 and citation `github_prs/PR-1230` leaves only C2-completeness. Real gap G (timeliness) is lost.
   This defeats the recorded deviation "so an LLM omission can't silently drop an exception". Suggestion: for check steps, fall back to the candidates' own citations, or re-raise the covered candidates when the finding is dropped.
2. **Cost totals are zeroed after human review.** `resume_audit` builds a new `Spend` (runner.py:55, 22-27), so report.md/report.json/run.json after `mockaudit review` show "US$0.0000 · 0 tokens · 0 LLM calls", and per-control `cost_usd` is 0. Reproduced with stub cost 0.01. The resumed run's cap counter also restarts at 0.
3. **The reviewer's decisions and notes are not persisted, and the edited file is overwritten.** On resume, `human_review` re-executes and rewrites `review_request.json` with blank decisions (graph.py:476). `decisions` live only in graph state, and report.py writes them nowhere. My test note "NOTE-XYZ" appears in no artifact. The spec asks for "approve or dismiss plus a note", and Phase 5 reuses this flow.
4. **"pass" in the Coverage table** (report.py:67; `ControlResult.status`). Consider "no exceptions" so nothing reads as a pass badge.
5. **"unresolved (reviewer and tester disagree)"** is also shown for skeptic errors (report.py:73). The C6 real-run finding is labelled as a disagreement although the skeptic produced no verdict.
6. **Skeptic calls blocked by the spend cap** become `unresolved` findings, not `spend_cap` errors (graph.py:391-400). This is acceptable under the criterion's "controls" wording, but the report doesn't say why. Also, with `max_concurrency>1`, in-flight calls can overshoot the cap: the guard runs before each call, but calls already in flight are not counted until they end.
7. **`RetryPolicy`** is listed in the CLAUDE.md architecture rules but not used. Retries come from `ChatOpenRouter(max_retries=2)` and ToolStrategy's single schema retry. No deviation records this.
8. **`mockaudit review` always builds `OpenRouterModels()`** (cli.py:98-101), so resuming a `--checks-only --review human` run needs `TESTER_MODEL`/`SKEPTIC_MODEL` set even though no LLM is used.
9. **A skeptic `revise` on a `judge: none` code finding** re-enters the tester with nothing to judge ("none (nothing to judge)"), and the unchanged finding is reviewed again. That's harmless, but it costs a second skeptic call.
10. **Two tester findings for the same step** get `-2` ids and can cover the same candidates, so the exceptions are counted twice across findings (graph.py:203-204).
11. In checks-only runs, `sample`/`samples` now list judgment-step items even though those steps are `not_tested`.

---

## Resolution (developer, 2026-10-16)

Both blocking items, note 1, and every smaller note are fixed, each with a regression test in `backend/tests/test_graph.py` (the "Phase 3 review fixes" section). Testing them also uncovered one more bug: the severity node stripped all `rule` reasoning steps; it now replaces only earlier severity steps. Re-run: 80 tests pass and ruff is clean. The real base run was not repeated. The fixes touch the revise, error and resume paths, which that run never reached, plus extra (code-verified) citations on tester findings.
