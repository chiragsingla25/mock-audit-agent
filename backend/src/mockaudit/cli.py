"""`mockaudit` command line. Phase 1: gen."""

from __future__ import annotations

import argparse
from pathlib import Path

from mockaudit.datagen.ledgerly import VARIANT_SEEDS, generate

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = REPO_ROOT / "data" / "ledgerly"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mockaudit", description="Mock SOC 2 audit over synthetic Ledgerly data")
    sub = parser.add_subparsers(dest="cmd", required=True)
    gen = sub.add_parser("gen", help="generate a Ledgerly dataset variant")
    gen.add_argument("--variant", choices=[*VARIANT_SEEDS, "all"], default="base")
    gen.add_argument("--seed", type=int, default=None, help="override the variant's default seed")
    gen.add_argument("--out", type=Path, default=DATA_ROOT, help="output root (default: data/ledgerly)")
    args = parser.parse_args(argv)

    if args.cmd == "gen":
        variants = list(VARIANT_SEEDS) if args.variant == "all" else [args.variant]
        for v in variants:
            out = generate(v, args.out, args.seed)
            print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
