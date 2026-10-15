# Mock Audit Agent

An AI that plays a skeptical SOC 2 Type II auditor against a company's controls and evidence, and predicts the exceptions a real auditor would raise before fieldwork starts. Each finding is written in auditor format and cites the exact records behind it.

**Status:** MVP scaffolded (2026-10-15). Next: Phase 0, the MVP notebook.

![Audit graph](docs/img/audit-graph.svg)

- [Spec](specs/2026-10-15-mock-audit-mvp.md): what gets built, phase by phase
- [Proposal](docs/proposal.md): approved architecture, stack, budget
- Background: [handover](docs/handover.md), [PRD](docs/PRD.md), [research](docs/research.md), [architecture](docs/architecture.md) (superseded by the proposal where they differ)

**Stack:** LangGraph, OpenRouter (Qwen tester, DeepSeek skeptic, US$10 cap), LangSmith, FastAPI, Next.js. Audits run offline; results are published as a static site on GitHub Pages.

## Setup

```bash
cp .env.example .env    # fill in your keys
cd backend && uv sync
```

## Roadmap (not in the MVP)

Recipe planner, skeptic escalation and reruns, sample extension, write-up quality judge, screenshot evidence, cross-control checks, multi-framework mapping, live integrations.
