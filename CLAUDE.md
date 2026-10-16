# Mock Audit Agent — project context

Portfolio MVP for Hyperproof outreach. It's a skeptical SOC 2 Type II auditor over a synthetic company (Ledgerly), predicting exceptions with cited records. **MVP only**: anything not in the spec goes to the README roadmap.

- Spec (source of truth for building): `specs/2026-10-15-mock-audit-mvp.md`
- Approved proposal: `docs/proposal.md` · diagram: `docs/img/audit-graph.svg`
- Background only (superseded where they differ): `docs/architecture.md`, `docs/PRD.md`, `docs/handover.md`, `docs/research.md`

## Commands

```bash
cd backend && uv sync                    # install (uv fetches Python 3.12 if missing)
uv run pytest                            # all tests (no LLM calls, no network)
uv run pytest tests/test_checks.py -k revocation   # one test
uv run ruff check .                      # lint
uv run mockaudit gen --variant base      # from Phase 1
uv run mockaudit run --variant base --review skip  # from Phase 3
uv run mockaudit eval --all              # from Phase 4
```

## Architecture rules

- One LangGraph `StateGraph` for the whole audit. Use `Send`, reducers, a conditional `START` edge, `interrupt` and `RetryPolicy`. **No hand-written asyncio runner, retry loop or orchestrator.**
- Exactly two LLM nodes: `tester` (LangChain `create_agent` + `ToolStrategy(TesterOutput)`, tools `get_record`, `read_policy`, `ask_owner`) and `skeptic_one` (one structured call per finding). Everything else is code.
- Orchestration is code: `dispatch_controls` and `route_after_skeptic` (max 1 revise round, re-entering the control subgraph at `tester`).
- Code does all counting, dates, SLAs and severity. The LLM never computes those, and severity is never set by an LLM.
- Checks run on the full population; the sample only chooses what the tester inspects for judgment-only steps.
- Every finding cites ≥ 1 existing record id; the citation check drops and logs the rest.
- Findings merge by `finding_id` (a reducer), so a revision can't change kept findings.
- Registries (`CHECKS`) are plain dicts. Don't build a framework.
- Compare timestamps in UTC. C2 = 24 clock hours. Period 2025-10-01 to 2026-09-30.
- Output is readiness, never an audit opinion; there is no pass badge anywhere.

## Models and budget

- Tester `TESTER_MODEL` (qwen/qwen3.5-flash-02-23; fallback qwen3.8-flash needs reasoning off), skeptic `SKEPTIC_MODEL` (deepseek/deepseek-v4-flash). They must be different families. Change them only through `.env`.
- US$10 total. Every LLM call appends `usage.cost` to `runs/spend.jsonl`; a run stops at `RUN_SPEND_CAP_USD`, the project at `PROJECT_SPEND_CAP_USD`.
- Tests use stub LLMs. **Never call OpenRouter from tests or CI.**

## Available resources

| Resource | Detail |
| --- | --- |
| Machine | MacBook Air, Apple Silicon, macOS; uv and Node installed; system Python 3.11 (uv provides 3.12) |
| Compute | No local GPU; all models go through OpenRouter |
| OpenRouter | Account with credits; **US$10 hard cap**; paid models only (no `:free`) |
| LangSmith | Free Developer plan (5k traces/month, 14-day retention) |
| GitHub | Account; public repo needed for free Pages |
| Data | Synthetic only (Ledgerly). No real company data |
| Org APIs | None (integrations are simulated) |

Secrets live only in the untracked `.env` (see `.env.example`). Never write keys into tracked files.

## Workflow

- Build phase by phase from the spec; stop at each phase gate for Chirag's approval.
- One test per acceptance criterion; the full suite passes before each commit.
- Record divergences in the spec's "Deviations from spec" section as they happen.
- Commit with the framework's `scripts/safe_commit.py`.
