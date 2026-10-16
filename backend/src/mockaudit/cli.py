"""`mockaudit` command line. Phase 1: gen. Phase 2: run --checks-only, eval --run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mockaudit.datagen.ledgerly import VARIANT_SEEDS, generate

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = REPO_ROOT / "data" / "ledgerly"
RUNS_DIR = REPO_ROOT / "runs"


def resolve_run(runs_dir: Path, run: str) -> Path:
    if run == "latest":
        latest = runs_dir / "LATEST"
        if not latest.exists():
            raise SystemExit(f"no runs yet in {runs_dir}; start one with `mockaudit run --checks-only`")
        run = latest.read_text().strip()
    path = runs_dir / run
    if not (path / "run.json").exists():
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
    run.add_argument("--checks-only", action="store_true", help="rules-only baseline: checks, no LLM")
    run.add_argument("--data-root", type=Path, default=DATA_ROOT)
    run.add_argument("--runs-dir", type=Path, default=RUNS_DIR)

    ev = sub.add_parser("eval", help="score a run against its answer key")
    ev.add_argument("--run", default="latest", help="run id, or 'latest'")
    ev.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    args = parser.parse_args(argv)

    if args.cmd == "gen":
        variants = list(VARIANT_SEEDS) if args.variant == "all" else [args.variant]
        for v in variants:
            print(f"wrote {generate(v, args.out, args.seed)}")
    elif args.cmd == "run":
        if not args.checks_only:
            print("agent mode arrives in Phase 3; use --checks-only for now", file=sys.stderr)
            return 2
        from mockaudit.checks_only import run_checks_only
        out = run_checks_only(args.variant, args.data_root, args.runs_dir)
        print(f"wrote {out} (checks-only, no LLM calls)")
    elif args.cmd == "eval":
        from mockaudit.scoring import evaluate_run, table
        print(table(evaluate_run(resolve_run(args.runs_dir, args.run))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
