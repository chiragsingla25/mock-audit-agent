VERDICT: FAIL

## Verdicts
Phase 1 (Schemas and Ledgerly dataset): FAIL. 5 of 7 criteria met. Criteria 4 and 6 each fail on one concrete data point, and each fix is small.

| # | Criterion | Verdict |
|---|---|---|
| 1 | gen writes layout; byte-identical rerun | PASS |
| 2 | Answer key G1–G10 tagged, traps, clean C1/C4/C9/C11, 7-rule severities | PASS |
| 3 | Documented raw-file query per gap/trap | PASS WITH NOTES |
| 4 | Noise present (incl. same-day suspension then later deletion) | FAIL |
| 5 | handover §11 edges have a row and a test | PASS |
| 6 | Variants A/B re-plant gaps (clarified: "on different records"), keys match | FAIL |
| 7 | Invalid controls.yaml entry names control and field | PASS WITH NOTES |

## Test suite
`cd backend && uv run pytest -q`: 18 passed, 0 failed (2.67 s). `uv run ruff check .`: all checks passed.

## What a user sees
- `uv run mockaudit gen --variant base --seed 7 --out <scratch>/g1` was run twice in place, and `gen --variant all --out <scratch>/g2` once. `diff -r g1/base g2/base` showed no differences, and `diff -r g2 data/ledgerly` showed none either, so the committed data equals fresh output. Under `PYTHONHASHSEED=123` the output is also identical. A stray file placed in `g1/base/exports/` is removed on rerun (the generator rmtree's the variant directory first).
- The spec's Verify line writes into the repo's `data/ledgerly`. I didn't run it there. The equivalent output in a temp directory is byte-identical to the committed data, and the test suite passes.
- The base `answer_key.yaml` reads cleanly: G1 2/18 high (rule 4), G2 1/19 high (r2), G3 1/4 high (r3), G4 1/8 high (r2), G5 4/320 high (r1), G6 2/8 moderate (r6), G7 3/53 moderate, G8 1/9 moderate, G9 3/30 moderate, G10 1/1 moderate. Traps T1–T4 are in C2/C1/C8/C9, and clean controls are C1, C4, C9, C11.
- Odd for a reader: the base noise row `suspend_then_delete` says "Suspended the same day", but the data shows the next day (see Phase 1 criterion 4).

## Phase 1 Schemas and Ledgerly dataset
| Criterion | Result | Evidence |
|---|---|---|
| 1 gen layout + byte-identical | PASS | `test_gen_writes_layout_and_twice_is_byte_identical` (reruns in place and into a second dir). Confirmed by hand: diff of fresh vs committed data, all 3 variants, is empty. |
| 2 Answer key | PASS | `test_answer_key_lists_gaps_traps_clean_controls` checks ids, tags, traps, clean controls and severities against a hard-coded research.md §4 table, so it is independent of `severity.py`. `test_severities_come_from_the_seven_rules` is tautological (the generator calls the same `severity()`), so I compared `severity.py:9-23` against architecture.md §6 by hand: the 7 rules match, first match wins, and the rate test is strictly > 10%. |
| 3 Documented queries | PASS WITH NOTES | `test_queries_find_every_gap_and_trap` on base/a/b. Each query reads raw CSV/MD only and is compared with key record ids. I also wrote my own checks for all 12 recipes (any worker type, real UTC elapsed time, PIR ≤ 15 bd, C7 ≤ 2 bd, sign-off ≤ 10 bd, C4 coverage, C11 in-period, annual training, out-of-period rows) and ran them over base/a/b. Every exception they raise matches the key or a trap, except for the C10 contractors (Note 1). |
| 4 Noise | FAIL | Name-format, time-zone, compliant-emergency and late-in-week-scan noise are present (`test_noise_is_present_and_not_a_gap`, plus manual inspection). The **same-day** suspension is not same-day in base: see "For the builder" item 1. The test only asserts `hours <= 24` (`test_dataset.py:306`), not same day. |
| 5 §11 edges | PASS | `test_domain_rule_edges`. Checked by hand: E1109 is terminated Fri 2026-08-28 18:00 AEST and suspended at OK-000260 (2026-08-30T23:00Z = Mon 09:00), 63.0 h, in G1. VULN-0020 runs 01-31 → 03-02, 30 days, not in G8. E1135 trained at exactly 30 days (pass). E1138 at 31 days is in G9. E1125 was hired 2025-12-15 and trained 2026-01-10 (26 days, pass). The generator skips DST weekends for the 63 h row (`ledgerly.py:206-207`). |
| 6 Variants | FAIL | `test_variants_replant_different_combinations` plus the queries test on a/b. Combinations differ (a: G2/G6/G10 dropped; b: G1/G5/G10 dropped), dropped controls become clean, and traps are re-placed. But the clarified "plant 7 of the 10 gaps on different records" isn't met for G3 in variant b, and the test exempts G3 explicitly: see "For the builder" item 2. |
| 7 Validation error | PASS WITH NOTES | `test_invalid_controls_yaml_names_control_and_field` (bad enum, missing field). I tried more by hand: unknown key gives `control C4: field 'colour': Extra inputs are not permitted`. A bad date gives `control C6: field 'period.0': ...month value is outside expected range`. Nested fields give `control C9: field 'test_recipe.0.judge'` and `control C10: field 'evidence.0.role'`. Others: `control X2: field 'control_id'`, duplicate id, a missing control_id (`control <entry 1>: field 'control_id'`), bad risk. All name the control and the field. Exceptions are in Notes 4–5. |

Adversarial inputs tried:
- 180 regenerations (seeds 1–60 × base/a/b) with the dataset queries and severity test run against each key. Every one generated and passed. The only mismatch is the G1 `hours` metadata at seed 46 (Note 3).
- 15 malformed controls.yaml inputs (listed above).
- A rerun into an existing directory that held a stray file: the file was removed.

## Regression sweep
BASE 0bdd115 had only the scaffold: an empty `mockaudit/__init__.py`, pyproject and docs. Phase 1 adds new modules only. The existing-file changes are a `[project.scripts]` entry in pyproject, the tester model swap in `.env.example`/CLAUDE.md (a Phase 0 ruling) and the spec text. No pre-existing code path changed, so this is effectively a new project and no old-vs-new comparison was needed.

## For the builder (failing criteria)
1. **Criterion 4, the same-day suspension is not same-day (base).** `ledgerly.py:218-222` gives the `sd_i` leaver a removal at `t + uniform(0.5, 23.5) h`, which can fall on the next day.
   - Reproduce: in `data/ledgerly/base`, E1066 is terminated `2026-03-18 16:15` (Sydney, = 05:15Z) and suspended at OK-000138 `2026-03-19T01:13:23Z` (12:13 local on the 19th). That is the next day in both local time and UTC.
   - The key's noise description (`ledgerly.py:282`, "Suspended the same day") is therefore wrong for base. Variants a (E1005) and b (E1008) are genuinely same-day.
   - Correct looks like: the suspend for `sd_i` falls on the termination's local date (and ideally the same UTC date), and the test asserts that, not just ≤ 24 h.
2. **Criterion 6, variant b re-plants G3 on the same record as base.** Base G3 = `UAR-2026Q3`, and variant b G3 = `UAR-2026Q3`. The cause is `ledgerly.py:337`: `rng.choice` over all 4 quarters can pick base's 2026Q3. `test_dataset.py:357` hides this with `or gid in ("G3",)`.
   - Reproduce: `grep -A6 "id: G3" data/ledgerly/{base,b}/answer_key.yaml`.
   - Correct looks like: variants choose from quarters other than base's (and the test exemption is removed). Alternatively, Chirag rules that G3 may repeat its record, and that ruling is logged in Deviations.

## Notes (never a reason to fail)
1. **Likely Phase 2/4 precision hit (worth a decision before Phase 2).** Each variant has 2 contractors hired in-period with no new-hire training: base C2017 (the T1 conversion record) and X3001. In a: C2035 and X3001. In b: C2041 and X3001.
   - Policy 2.1 (`policies.py:77`) says "New hires", not employees, and the C10 `days_after_event` params (`datagen/controls.yaml:175`) have no worker-type filter.
   - Only the test query filters `worker_type == "employee"` (`test_dataset.py:158`).
   - A Phase 2 check that follows the recipe literally will raise 2 C10 exceptions that aren't in the key.
   - Suggest either "New-hire employees" in policy 2.1 plus a `where: {worker_type: employee}` param, or listing them in the key. The same applies to the C10 annual `population_diff` (line 177), although its policy text does say "employees".
2. Mislabelled noise: the `signoff_after_period` entry is tagged `control_id: C3` but lists `PAR-2026Q3`, which is a C5 record (`ledgerly.py:392-394`). In base it lists only the PAR, because the UAR is the unsigned G3.
3. Wall-clock datetime arithmetic: `t + timedelta(...)` on Sydney-aware datetimes (`ledgerly.py:211, 213, 218`), and the same-tzinfo subtraction at `:263`, ignore DST.
   - At seed 46 the key's G1 `hours` are [63.0, 219.0], but the real elapsed time is [63.0, 220.0] (a/b: 185 vs 186).
   - Record ids and counts were right in all 180 seeds, and seeds 7/11/23 are unaffected.
   - Fix: do the arithmetic in UTC.
4. A reversed `period` reports `field '<root>': ... period start is after period end`, which names the control, but the field appears only in the message text. Also, a YAML syntax error raises a raw `yaml.ParserError` with no control named, and unknown `check` names aren't validated (the CHECKS registry arrives in Phase 2).
5. `load_controls` accepts 11 controls. Nothing enforces "ControlSpec × 12".
6. The C8 30-day edge VULN-0020 is 30 days by date but 30 d 6 h elapsed (opened 10:00Z, closed 16:00Z). The Phase 2 `sla_days` check must count calendar dates, as the key assumes, or it will flag this row.
7. The weekend 63 h and 30/31-day edges exist only in base. Variants use random late values (G9 a: 44/49; b: 49/52/56). The criterion doesn't require them in variants.
8. `gen --variant all --seed N` applies the same seed to all three variants. That's harmless, but surprising.

---

## Resolution (developer, 2026-10-16)

Both FAIL items and the notes listed in the spec's Deviations ("phase 1 / review gate") are fixed. Not changed: unknown check names and the 12-control count are not validated at load time (Phase 2 validates check names against `CHECKS`). Re-run: 19 tests pass, ruff is clean, and the seed sweep over 180 datasets has 0 failures.
