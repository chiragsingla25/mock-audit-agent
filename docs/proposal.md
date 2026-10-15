# Proposal — Mock Audit Agent (MVP)

From: app-architect · Date: 2026-10-15 · Status: **awaiting approval**
Inputs: [handover.md](handover.md) (intake), [PRD.md](PRD.md), [research.md](research.md), [architecture.md](architecture.md) (design preference). Where they differ, this proposal wins.

**Scope rule: MVP only.** Build the smallest thing that proves the agent finds planted gaps, cites real records, avoids traps, and beats a rules-only run, with its cost measured. Everything else goes in the README under "Roadmap".

## 1. Problem and audience

This is a portfolio demo for Hyperproof outreach. It plays a skeptical SOC 2 Type II auditor against a synthetic company, Ledgerly (12 controls, 10 planted gaps, 4 clean controls, about 4 traps), and predicts the exceptions a real auditor would raise. Each finding is written in auditor format and cites exact records. It is pitched as the customer-side, pre-audit extension of Hyperproof's AI evidence validation. The audience is the Hyperproof hiring team. Effort: about **4 weeks of evenings**. Demo only: no monitoring and no production hardening.

## 2. Prior art and scope

- **Copying:** Hyperproof's "AI suggests, human validates" review, Thoropass's "forecast before fieldwork" framing, and evidence-linked findings with citations.
- **Our angle:** populations and samples, auditor-format findings, and **accuracy measured against an answer key and against a rules-only baseline.**
- **In the MVP:** CLI audit runs, the local live app (start an audit, watch progress, review findings with a simple reasoning list, approve or dismiss, export the report), a static showcase on GitHub Pages, and the evaluation in the README.
- **Roadmap (not built):** recipe planner, skeptic escalation and human-triggered reruns, automatic sample extension, citation repair, the skeptic reviewing dismissals, the write-up quality judge, observations (C6 approver-commits), screenshots and vision, SQL queries over exports, an evaluation screen in the UI, cross-control checks, multi-framework support, live integrations.

## 3. Decisions confirmed at intake (2026-10-15)

| Item | Decision |
| --- | --- |
| Observation period | **1 Oct 2025 – 30 Sep 2026**. Quarters are Q4-25, Q1-26, Q2-26, Q3-26 |
| Quarterly sign-off window (C3/C5) | 10 business days after quarter end, stated in the policy file |
| C2 24 hours | 24 clock hours (locked) |
| C6 approver who also committed | Not planted in the MVP (roadmap) |
| GRC practitioner review | Not for now. The README says findings were checked against published auditor guidance only |

## 4. Architecture

**Pattern:** a deterministic pipeline per control with **one agentic node** (`tester`), followed by **one reviewer call** (`skeptic`), all in one LangGraph `StateGraph`. The orchestration is code. It is not multi-agent.

![Audit LangGraph flow](img/audit-graph.svg)

| Node | Type | Does |
| --- | --- | --- |
| `load_specs` | code | Load and validate `controls.yaml` into `ControlSpec` |
| `dispatch_controls` | code orchestrator | `Send` × 12 control runs, `max_concurrency=4` |
| `population_check` | code | Reconcile the population against an independent source and list missing items |
| `run_checks` | code | Run every recipe check over the **full population**, producing candidates (check failures plus missing items) |
| `sample` | code | Seeded sample for judgment-only steps |
| `tester` | **LLM** (Qwen) | Raise or dismiss each candidate with citations; handle judgment-only steps. Tools: `get_record`, `read_policy`, `ask_owner`. `create_agent(..., response_format=ToolStrategy(TesterOutput))` |
| `finalize` | code | Drop and log findings with nonexistent citations; attach coverage and reasoning steps |
| `skeptic_one` | **LLM** (DeepSeek) | One structured call per finding, fanned out with `Send`: keep, revise or reject |
| `route_after_skeptic` | code orchestrator | `revise` items → `Send` only those controls back in at `tester` (**max 1 round**); else → `severity`. Nothing to review → `severity` |
| `severity` | code | 7 deterministic rules |
| `human_review` | human | `interrupt()`; FastAPI resumes with the approve/dismiss decisions. Skipped when `review_mode: skip` (evaluation runs) |
| `report` | code | Template: approved findings, coverage per control, a remediation task each |

**Flow rules**

- Findings merge per `finding_id` (reducer), so a revision can't overwrite kept findings. A revise run enters the control subgraph at `tester` and reuses the population, checks and sample.
- Fan-in: the skeptic step waits for every control branch (LangGraph superstep).
- An error, a timeout (`asyncio.wait_for` in `tester`) or the spend cap gives that control `status: error`, and the run continues.
- Rejected findings stay visible in the review UI as "rejected by skeptic".
- **Checks-only baseline:** a run-config flag replaces `tester` with a code node that raises every candidate, and skips the skeptic. No LLM.
- **Reasoning view (simple):** `finalize` turns the tester's messages and check results into a list of `ReasoningStep`s (`check` / `tool` / `owner` / `llm` / `rule`) for each finding and each dismissed candidate. The UI and the static site show it as a plain step list.
- **Tracing:** LangSmith via environment variables. Base traces are kept 14 days, so the static site uses the reasoning lists, not LangSmith links.
- **Spend cap:** each call's OpenRouter `usage.cost` is appended to `runs/spend.jsonl`. A run stops at US$1 and the project stops at US$9.50. Chirag sets a US$10 limit on the OpenRouter key.

## 5. Stack (locked) and versions (checked 2026-10-15)

| Layer | Choice |
| --- | --- |
| Agent | LangGraph 1.2 (`StateGraph`, `Send`, reducers, `interrupt`) + LangChain 1.4 `create_agent`; `langgraph-checkpoint-sqlite` (needed for the paused review) |
| LLM client | `langchain-openrouter` (`ChatOpenRouter`); `ChatOpenAI` + OpenRouter base URL as a fallback |
| Models | Tester `qwen/qwen3.8-flash` (US$0.15 / 0.47 per M); skeptic `deepseek/deepseek-v4-flash` (0.091 / 0.182); a different family, as locked. Bake-off fallback for the tester: `qwen/qwen3.5-flash-02-23` |
| Backend | Python 3.12 (uv), Pydantic 2, SQLite, FastAPI (local only) |
| Tracing | LangSmith (free Developer plan) |
| Frontend | Next.js 16. **Live mode** (local, polls FastAPI) and **showcase mode** (static export from JSON). Four screens: start, progress, findings + review, report |
| Deploy | Audits run offline on the Mac → `export-showcase` → GitHub Actions → GitHub Pages |

## 6. Budget (US$10 cap; estimates until Phase 0 measures them)

| Bucket | US$ | Covers |
| --- | --- | --- |
| Phase 0 bake-off | 0.50 | 2 testers × C2 × 3 repeats, plus the skeptic |
| Development | 2.50 | Prompt iteration, dry runs |
| Evaluation | 2.00 | Base + 2 variants, 3 stability runs on base (about 6 audits at about US$0.25). Skeptic-off and checks-only cost nothing extra |
| Showcase runs | 0.50 | Final published runs |
| Headroom | 4.50 | Not spent without a decision |

## 7. Verification

- Golden answer key: 10 gaps (each tagged `code` or `judgment`), about 4 traps, 4 clean controls.
- Metrics, all scored by code: gap recall (≥ 8/10), precision (≥ 80%), clean-control accuracy (4/4), citation validity (100%), severity agreement (≥ 80%), stability (≥ 90% overlap), **agent vs checks-only**, skeptic on vs off, cost per audit.
- CI: pytest (checks, schemas, severity, scorer, exporter, generator invariants), validation of the showcase JSON, and the frontend build. No LLM calls or secrets in CI.

## 8. Delivery model

**Single builder plus review gates** at the end of Phase 1 (dataset and answer key) and Phase 3 (audit graph), plus a review at each milestone. Gates are per phase; Chirag can waive named gates (continuous mode).

## 9. Phases

| Phase | Delivers | Verify |
| --- | --- | --- |
| 0. MVP notebook | C2 end to end on hand-built data: checks → tester → skeptic; 2 testers × 3 repeats including 1 trap; cost measured | `notebooks/mvp.ipynb` → per-model table (G1/G2 found, trap dismissed, US$ per control) |
| 1. Schemas + Ledgerly | Pydantic schemas, `controls.yaml` (12 recipes), seeded generator, traps, answer key, 2 variants **[review gate]** | `uv run mockaudit gen --variant base && uv run pytest tests/test_dataset.py` → passes |
| 2. Checks + scoring | `CHECKS`, severity, citation check, scorer, `--checks-only` | `uv run mockaudit run --checks-only && uv run mockaudit eval` → recall and precision table |
| 3. Audit graph | Full `StateGraph` (all 12 controls), skeptic, 1 revise round, `interrupt`, spend cap, LangSmith **[review gate]** | `uv run mockaudit run --review skip` → 12 results; a revise visible in LangSmith; spend logged |
| 4. Evaluation + CI | Base + 2 variants, stability, skeptic on/off, checks-only comparison, `ci.yml`. **Milestone 1** | `uv run mockaudit eval --all` → `eval.json`; CI green |
| 5. Local app | FastAPI + Next.js live mode: start, progress, findings with reasoning list + approve/dismiss, report export | Start an audit → 12 cards finish → open G1 → step list shows → approve → export Markdown |
| 6. Showcase + ship | `export-showcase`, static build, Pages deploy, README (evaluation + roadmap), video script. **Milestone 2** | Push to `main` → the Pages URL shows the runs, findings, reasoning lists and the comparison |

The outreach email is Chirag's task after Phase 6.

## 10. Risks

- Qwen and DeepSeek Flash are reasoning models, so hidden reasoning tokens are billed. Phase 0 measures this; reasoning effort is set in config.
- The tester's structured output fails through ToolStrategy: retry once with the error, then try `ProviderStrategy` or the fallback tester.
- Cheap-model recall comes in below 8/10: code does all counting, tool schemas are tight, and a missed target is reported honestly.
- Traps make checks-only precision look worse. That's intended; it's the story.
