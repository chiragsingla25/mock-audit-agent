# Handover to app-architect — Mock Audit Agent

> **Superseded where it differs** by [proposal.md](proposal.md) (approved MVP, 2026-10-15) and [the spec](../specs/2026-10-15-mock-audit-mvp.md). Kept as background.


From: kickoff (quick) · Date: 2026-10-15 · Status: ready for architect
Read in this order: this file → [PRD.md](PRD.md) → [research.md](research.md) → [architecture.md](architecture.md) (design preference)
App-architect: treat sections 1–7 as your intake (step 1). Confirm, don't re-ask.
Sections marked "preference" are open to your research and pushback.

## 1. One-paragraph brief

The Mock Audit Agent plays a skeptical SOC 2 Type II auditor against a synthetic company ("Ledgerly": 12 controls, 10 planted gaps, 4 clean controls) and predicts the exceptions a real auditor would raise, each written up in auditor format with the exact records it cites. It is a **portfolio piece** to get an interview at **Hyperproof**, positioned as the customer-side, pre-audit extension of Hyperproof's AI evidence validation. Audits run **offline on Chirag's Mac** through cheap OpenRouter models under a **US$10 cap**; pre-computed results, the evaluation and trace summaries are published as a **static GitHub Pages site**, then a 2-minute video and the outreach email.

## 2. Problem and who it's for

**Problem.** Most audit exceptions are found by the external auditor during fieldwork, when they're expensive to fix. In Thoropass's 2026 survey, 91% said they must resubmit audit evidence at least sometimes. Today's GRC AI (Hyperproof, Vanta, Drata) mostly validates individual evidence items; none publicly simulates populations, sampling and auditor-style findings with measured accuracy. Detail: [research.md §2](research.md).

| Persona | Need | What they get |
| --- | --- | --- |
| Hyperproof hiring team (primary audience) | Proof Chirag can build and evaluate production-style agentic AI in their domain | Pages site with runs, findings, evaluation; video; repo |
| GRC lead (product user, simulated) | Know where the audit will hurt, weeks early | Findings with cited evidence, coverage per control, remediation tasks |
| Control owner (simulated) | Know exactly what to fix or provide | One precise finding per gap |

## 3. Purpose, stakes and effort tier

| Item | Answer |
| --- | --- |
| Purpose | Portfolio / interview piece (Hyperproof outreach). Verify and ship sized accordingly |
| Scale | Demo audience only. No live traffic; nothing runs online. No monitoring needed |
| Effort tier | Sustained project: about 5 weeks of evenings |
| Deadline | None fixed (assumption) |

## 4. Goals, success metrics and evaluation story

**Goals:** run a mock audit over 12 controls; catch planted gaps with valid citations; produce auditor-format findings with rule-based severity; human review before the report; publish a measured evaluation.

| Metric | Target | How measured |
| --- | --- | --- |
| Gap recall | ≥ 8 of 10 | Code: finding matches an answer-key gap on control id and ≥ 1 cited record id |
| Precision | ≥ 80% | Code: matching findings ÷ all kept findings |
| Clean-control accuracy | 4 of 4 | Code: C1, C4, C9, C11 produce no findings |
| Citation faithfulness | 100% | Code: cited records exist; judge: they support the claim |
| Severity agreement | ≥ 80% | Code: rule-based severity vs answer key |
| Write-up quality | Average ≥ 4 of 5 | LLM judge with rubric (condition, criteria, cause, effect, recommendation) |
| Stability | ≥ 90% finding overlap | Code: repeated runs on the same data (run count set by budget) |
| Skeptic value | Report both | Precision with vs without the skeptic; unresolved count |
| Cost per audit | Report | Tokens and US$ from traces |

**Evaluation story — the questions the eval must answer**

1. Did it find each planted gap, on the right control, citing the right records?
2. Did it stay quiet on the clean controls (no invented findings)?
3. Is every cited record real, and does it actually show what the finding claims?
4. Is the severity what the rules say it should be?
5. Would an auditor accept the write-up (condition, criteria, cause, effect, recommendation)?
6. Does the skeptic remove false positives without dropping real gaps?
7. Are results stable across runs and across re-planted dataset variants?
8. What does one audit cost, and does the whole plan fit in US$10?

**Judge independence:** the tester is a Qwen-family model; the skeptic and the write-up judge must be a different model family.

## 5. Scope and key flows

**In scope:** SOC 2 Type II, 12 controls (11 Security + 1 Availability), 12-month period; Ledgerly synthetic data with noise; per-control audit runs; skeptic pass; rule-based severity; human review in the local UI; report with coverage and remediation tasks; evaluation; static showcase on GitHub Pages.

**Out of scope:** live integrations (Okta, AWS, GitHub; exports are simulated); frameworks other than SOC 2; any audit opinion or "pass" badge; an LLM planner that writes test recipes (v2); live audits online; auth, multi-tenancy, production hardening.

**Candidate overkill cuts (if time or budget runs short):** the evaluation screen in the UI (keep it in the README); stability and variant runs beyond what US$10 allows; screenshot evidence (vision calls).

**Key flows**

1. *Run (local):* pick dataset variant → start audit → watch per-control progress → results saved.
2. *Review (local):* open a finding → see cited records, agent reasoning, skeptic verdict → approve or dismiss.
3. *Report:* approved findings + coverage per control + remediation tasks → export.
4. *Publish:* export selected runs as JSON → push → GitHub Actions builds and deploys the static site.
5. *Browse (visitor):* open the Pages site → pick a run → explore findings, evidence, verdicts, evaluation.

## 6. Available resources (for CLAUDE.md, no secrets)

| Resource | Detail |
| --- | --- |
| Local machine | MacBook Air, Apple Silicon (arm64), macOS. Python and Node toolchains in use on other projects |
| Heavy compute | None local. All model calls go to OpenRouter; the MVP notebook runs locally on the Mac |
| GitHub | Account available; repo public (needed for free Pages and the outreach link) |
| OpenRouter | Account with credits. **Hard cap US$10** for the whole project. Paid cheap models throughout (no `:free` variants) |
| Other services | None required (no database service; SQLite locally) |
| Org / proprietary APIs | None. Hyperproof APIs are not used; integrations are simulated |

## 7. Constraints and preferences

| Item | Value | Tag | Reason |
| --- | --- | --- | --- |
| Orchestration | LangGraph | locked | Chirag's production experience; matches the pitch |
| LLM access | OpenRouter, one API for all models | locked | One key, easy model swaps |
| Models | Cheapest viable: Qwen-family tester; skeptic and judge from a different cheap family; exact IDs by architect | locked (constraints), architect (IDs) | US$10 cap; cross-family judge avoids self-preference bias |
| Budget | US$10 total, paid models throughout | locked | Chirag's call |
| UI | Next.js frontend + FastAPI backend (local); static export for showcase | locked | Polished UI; uses Chirag's TypeScript |
| Deployment | Audits offline; pre-computed results on GitHub Pages | locked | Free, no secrets online, no public spend |
| Agent design | One async run per control (schema in, structured out); code does counting; separate swappable skeptic; targeted revisions (max 2); rule-based severity; coverage statement, no pass badge. Full detail: [architecture.md](architecture.md) | **preference** | Designed in discussion; architect may propose a better shape with evidence |
| Pattern hunch | Per-control tool-using agent + separate reviewer; dynamic behaviour = deciding which records to inspect and when to ask the owner | preference | Architect step 3 |
| Storage | SQLite + JSON run artifacts | preference | Simple, local |
| Observability | MLflow tracing locally; trace summaries exported for the site | preference | Chirag's production stack |
| Language | Python backend, TypeScript frontend | locked | Follows from the locked stack |
| Security / privacy | Synthetic data only; OpenRouter key only in local `.env`; nothing secret in CI or the site | locked | Public repo and site |

## 8. Locked decisions

| # | Decision | Why |
| --- | --- | --- |
| L1 | LangGraph, OpenRouter, Next.js + FastAPI, GitHub Pages with offline runs | Chosen deliberately by Chirag |
| L2 | Cheapest viable models; tester and judge from different families | US$10 cap; judge independence (past-project lesson) |
| L3 | US$10 hard cap, paid cheap models throughout | Chirag's call |
| L4 | C2 "within 24 hours" means 24 clock hours; weekends not excused | Matches the control text; strict auditor reading |
| L5 | Output is readiness, never an audit opinion; no pass badge | Avoids false confidence |
| L6 | Every finding cites ≥ 1 real record id | Core guard against invented findings |

## 9. For the architect to decide or verify

1. **Agent design (preference):** confirm or challenge [architecture.md](architecture.md) D1–D12 with evidence.
2. **Exact OpenRouter model IDs** for tester, skeptic and judge: cheapest that reliably do tool calling and structured output; cross-family constraint; record prices.
3. **Budget plan:** measure tokens and US$ per audit in the MVP notebook, then size variant, stability and skeptic-on/off runs to fit US$10 with headroom for development. My rough estimate (not measured) is US$0.30–0.50 per full audit.
4. **Fallbacks if cheap models underperform:** e.g. tighter tool schemas, fewer free-form steps, more checks in code, before considering a pricier tester (which would need Chirag's approval against the cap).
5. Verification depth (portfolio: golden answer key plus CI unit tests, no LLM calls in CI).
6. Delivery model (default single builder; review gate at the end of the agent-graph phase is worth considering).
7. Phase gates vs continuous mode for later phases.
8. **MVP notebook target:** control C2 end to end (population check, sample, tester, structured `ControlResult`, skeptic verdict), run locally on the Mac.
9. Next.js static export for GitHub Pages (basePath, static params for every run/control/finding page).
10. LangGraph pattern for a tool loop ending in validated structured output, with a checkpointer for `revise()`.

## 10. Data

- **Source:** fully synthetic, generated by a seeded Python script. No real company data; no licensing issues.
- **Company:** Ledgerly, fictional B2B invoicing SaaS; ~120 employees, 30 hires, 18 terminations, ~900 deployments, 52 weekly scans, 4 quarterly reviews, 6 incidents, 15 vendors (5 critical); period 2026-01-01 to 2026-12-31.
- **Files:** controls spec, policies, exports (HR, Okta, IAM, GitHub, deploys, scanner, Jira, LMS, vendors), review artifacts, scripted owner answers, answer key.
- **Answer key:** 10 planted gaps with rule-based severities, 4 clean controls, plus deliberate noise that is *not* a gap. Full table: [research.md §4](research.md).
- **Variants:** gaps re-planted in random combinations; number of variants set by budget.

## 11. Domain rules and edge cases

| Rule | Ordinary input to check | Expected result |
| --- | --- | --- |
| C2: access removed within 24 h of termination | Termination Friday 18:00, Okta suspend Monday 09:00 | Exception (24 clock hours; L4) |
| C2: "removed" = first suspend or deactivate event | Suspended same day, deleted 6 days later | Pass (suspension removes access) |
| C2: population completeness vs HR | HR termination with no Okta account at all (contractor never provisioned) | Not an exception; note it, don't flag a missing deactivation |
| C3/C5: quarterly review with sign-off | Q3 review signed 3 days after quarter end | Pass if within policy window; architect to confirm window (assume 10 business days) |
| C6: author ≠ approver | PR approved by a second person who also pushed a commit to it | Flag for review: approver is also an author; architect to confirm treatment |
| C7: emergency change approved within 2 business days | Hotfix Friday, approval Tuesday | Pass (2 business days: Mon, Tue) |
| C8: weekly scan | Scan run Sunday one week, Monday the next | Pass (each calendar week has a scan) |
| C8: critical fixed within 30 days | Opened Jan 31, closed Mar 2 (30 days in a leap-free year) | Pass at exactly 30 days; fail at 31 |
| C10: training within 30 days of hire | Hire on Dec 15, training Jan 10 | Pass; cross-year dates handled |
| C12: restore test in period | Test dated Dec 31 of prior year | Exception (evidence outside period) |
| Time zones | HR export in AEST, Okta in UTC | Compare in UTC; no false late revocations |

## 12. Risks

| Risk | Mitigation |
| --- | --- |
| US$10 cap exhausted before final runs | Measure cost per audit in the MVP notebook; scale variants/stability runs; cache extractions; stop runs at a spend threshold |
| Cheap models weak at tool use → recall below 8/10 | Code does all counting; tight tool schemas; fewer free-form steps; report honestly if a target is missed |
| Cross-family skeptic too strict or too lenient | Measure skeptic on vs off; tune prompt; keep human review |
| Hallucinated findings | Mandatory citations, code citation check, skeptic, human approval |
| Synthetic data too easy | Noise, clean controls, re-planted variants |
| False confidence ("passed the mock audit") | Coverage statement per control; no pass badge |
| Next.js UI eats week 5 | Fallback: minimal UI (progress, review, report); evaluation in README |
| Domain inaccuracy | Sample sizes and test steps from published auditor guidance; ask a GRC practitioner if possible |

## 13. Prior-art seed

Closest: **Thoropass** (auditor-side agents: evidence sorting, first-pass checks, audit copilot, reviewer AI; markets a "mock audit forecast"); **Vanta, Drata, Hyperproof** (item-level evidence validation); **Comp AI** (open-source evidence collection). **Novelty: medium** — the category exists, but no public tool simulates populations, sampling and auditor-style findings on the customer side with measured accuracy. Table stakes: evidence mapped to controls, citations, human review. Overkill here: integrations, multi-framework. Detail: [research.md §2–3](research.md).

## 14. Expected output from the architect

- `docs/proposal.md` (framework format) and the phased spec, building on this handover and [architecture.md](architecture.md).
- Anything here the architect disagrees with, and why — especially the agent-design preference and the budget plan.

## 15. Files and links

| File / link | What it is |
| --- | --- |
| [PRD.md](PRD.md) | Product requirements |
| [research.md](research.md) | Domain primer, prior art, data design, technical notes, sources |
| [architecture.md](architecture.md) | Detailed agent design from the 2026-10-14 discussion (a **preference**, not locked) |
| [Living project doc](https://claude.ai/code/artifact/cc06b2ff-8676-47d2-bdb9-3de1f130b07d) | Earlier research doc; superseded where it differs |

## 16. Open questions

- [ ] Which runs to publish on the site (baseline, variants, skeptic on/off) — depends on budget.
- [ ] Can a GRC or audit practitioner review the findings report before outreach?
- [ ] Review window for quarterly sign-offs (assumed 10 business days).
- [ ] Treatment of approvers who also committed to a PR (C6).

## 17. Assumptions

- No fixed deadline; ~5 weeks of evenings. *Changes if:* Chirag sets a date → cut to the overkill list.
- Cost per audit US$0.30–0.50 on Qwen-class pricing (estimate, unmeasured). *Changes if:* the MVP notebook measures more → fewer variants and stability runs.
- Free OpenRouter models are not used, per Chirag. *Changes if:* the cap gets tight → revisit using `:free` variants for development only.

## Appendix — Kickoff log

### Session 2026-10-15 (quick)

Converted from the 2026-10-14 handover; prior answers taken from the design discussion and existing docs.

- Q: Treat the agent design (async per control, separate skeptic, targeted revisions, code for counting, rule-based severity) as locked or preference? → A: Preference (preference)
- Q: Stack (LangGraph, OpenRouter, Next.js + FastAPI, GitHub Pages offline runs) firm or preference? → A: Lock all four (locked)
- Q: OpenRouter account and spend cap? → A: Have account, cap US$10, cheapest models possible, like Qwen (locked)
- Q: C2 24-hour rule for a Friday-evening termination? → A: 24 clock hours (locked)
- Q: Model setup under the cap? → A: Qwen tester + other-family skeptic and judge; architect picks IDs (locked constraints / architect IDs)
- Q: Free models for development or paid throughout? → A: Paid cheap models throughout (locked)
- Restated brief confirmed: yes (2026-10-15)
