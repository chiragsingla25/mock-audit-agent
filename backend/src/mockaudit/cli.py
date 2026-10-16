"""`mockaudit` command line: gen, run (agent / --skeptic-off / --checks-only), review, eval."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from mockaudit.datagen.ledgerly import VARIANT_SEEDS, generate

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = REPO_ROOT / "data" / "ledgerly"
RUNS_DIR = REPO_ROOT / "runs"


def load_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")


def print_summary(out: dict, mode: str) -> None:
    if out["status"] == "done":
        print(f"wrote {out['run_dir']} ({mode}): {out['findings']} findings in the report · "
              f"cost US${out['cost_usd']:.4f} · {out['tokens']:,} tokens · {out['llm_calls']} LLM calls")


def resolve_run(runs_dir: Path, run: str, need: str = "run.json") -> Path:
    if run == "latest":
        latest = runs_dir / "LATEST"
        if not latest.exists():
            raise SystemExit(f"no runs yet in {runs_dir}; start one with `mockaudit run --checks-only`")
        run = latest.read_text().strip()
    path = runs_dir / run
    if not (path / need).exists():
        raise SystemExit(f"run {run!r} not found in {runs_dir}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mockaudit", description="Mock SOC 2 audit over synthetic Ledgerly data")
    sub = parser.add_subparsers(dest="cmd", required=True)
    gen = sub.add_parser("gen", help="generate a Ledgerly dataset variant")
    gen.add_argument("--variant", choices=[*VARIANT_SEEDS, "all"], default="base")
    gen.add_argument("--seed", type=int, default=None, help="override the variant's default seed")
    gen.add_argument("--out", type=Path, default=DATA_ROOT, help="output root (default: data/ledgerly)")

    run = sub.add_parser("run", help="run an audit over a dataset variant")
    run.add_argument("--variant", choices=list(VARIANT_SEEDS), default="base")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--checks-only", action="store_true", help="rules-only baseline: checks, no LLM")
    mode.add_argument("--skeptic-off", action="store_true", help="tester only, no skeptic review")
    run.add_argument("--review", choices=["skip", "human"], default="skip")
    run.add_argument("--controls", default=None, help="comma-separated subset, e.g. C2,C8")
    run.add_argument("--data-root", type=Path, default=DATA_ROOT)
    run.add_argument("--runs-dir", type=Path, default=RUNS_DIR)

    rv = sub.add_parser("review", help="resume a paused run with approve/dismiss decisions")
    rv.add_argument("--run", required=True, help="run id, or 'latest'")
    rv.add_argument("--decisions", type=Path, required=True, help="the edited review_request.json")
    rv.add_argument("--runs-dir", type=Path, default=RUNS_DIR)

    ev = sub.add_parser("eval", help="score a run against its answer key")
    ev.add_argument("--run", default="latest", help="run id, or 'latest'")
    ev.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    args = parser.parse_args(argv)

    if args.cmd == "gen":
        variants = list(VARIANT_SEEDS) if args.variant == "all" else [args.variant]
        for v in variants:
            print(f"wrote {generate(v, args.out, args.seed)}")
    elif args.cmd == "run":
        import asyncio

        from mockaudit.runner import new_run_id, run_audit
        from mockaudit.schemas import RunConfig
        mode = "checks_only" if args.checks_only else "skeptic_off" if args.skeptic_off else "agent"
        models = None
        if mode != "checks_only":
            load_env()
            from mockaudit.llm import OpenRouterModels
            models = OpenRouterModels()
        cfg = RunConfig(run_id=new_run_id(mode, args.variant), variant=args.variant, mode=mode, review_mode=args.review,
                        tester_model=getattr(models, "tester_name", ""), skeptic_model=getattr(models, "skeptic_name", ""),
                        max_concurrency=int(os.environ.get("MAX_CONCURRENCY", "4")),
                        control_timeout_s=int(os.environ.get("CONTROL_TIMEOUT_S", "420")),
                        run_spend_cap_usd=float(os.environ.get("RUN_SPEND_CAP_USD", "1.00")),
                        controls=args.controls.split(",") if args.controls else None)
        out = asyncio.run(run_audit(cfg, args.data_root, args.runs_dir, models))
        print_summary(out, mode)
        if out["status"] == "paused":
            print(f"paused for review: edit {out['review_request']}, then run "
                  f"`mockaudit review --run {cfg.run_id} --decisions <file>`")
    elif args.cmd == "review":
        import asyncio
        import json

        from mockaudit.runner import resume_audit
        load_env()
        from mockaudit.llm import OpenRouterModels
        run_dir = resolve_run(args.runs_dir, args.run, need="config.json")
        out = asyncio.run(resume_audit(run_dir, json.loads(args.decisions.read_text()), OpenRouterModels()))
        print_summary(out, "review")
    elif args.cmd == "eval":
        from mockaudit.scoring import evaluate_run, table
        print(table(evaluate_run(resolve_run(args.runs_dir, args.run))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
