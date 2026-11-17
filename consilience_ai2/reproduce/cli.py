"""``consilience-ai2 reproduce check <record.yaml> [--repo PATH] [--json OUT]``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from consilience_ai2.reproduce.comparability import BACKENDS
from consilience_ai2.reproduce.verdict import CHECKS, check_file

DEFAULT_OUT = "reproduction_verdict.json"


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "reproduce", help="reproduction verdict from the numbers (asta-flows rubric)",
        description="Judge a reproduction record on the asta-flows secondary-reproduction "
                    "axes (faithfulness, decidability, outcome) from its numbers, and check "
                    "that the thresholds were committed first and the hypothesis copied "
                    "verbatim. Codes: S1 F1 D1 V1 P1 P2.")
    sub = p.add_subparsers(dest="reproduce_command", metavar="<subcommand>")
    c = sub.add_parser("check", help="check one record and write reproduction_verdict.json")
    c.add_argument("record", help="the reproduction record (YAML or JSON)")
    c.add_argument("--repo", metavar="PATH",
                   help="git repository for the commit-order check (default: the one "
                        "holding the record)")
    c.add_argument("--json", metavar="OUT",
                   help=f"where to write the verdict (default: {DEFAULT_OUT} beside the "
                        "record; '-' for standard output)")
    c.add_argument("--backend", choices=BACKENDS, default="auto",
                   help="comparability backend for F1 (default: consilience when installed)")
    c.add_argument("--pack", metavar="PACK",
                   help="consilience compare pack for the conditions (name or path)")
    c.add_argument("--skip", metavar="CODE", action="append", default=[], choices=CHECKS,
                   help="skip a check (repeatable)")
    c.set_defaults(func=run_check)
    p.set_defaults(func=lambda args: (p.print_help(sys.stderr), 2)[1])


def run_check(args: argparse.Namespace) -> int:
    record = Path(args.record)
    if not record.exists():
        print(f"consilience-ai2 reproduce: no such file: {record}", file=sys.stderr)
        return 2
    try:
        report = check_file(record, repo=args.repo, backend=args.backend, pack=args.pack,
                            skip=tuple(args.skip))
    except ValueError as exc:  # e.g. --backend consilience without the package
        print(f"consilience-ai2 reproduce: {exc}", file=sys.stderr)
        return 2
    if args.json == "-":
        sys.stdout.write(report.to_json())
    else:
        out = Path(args.json) if args.json else record.with_name(DEFAULT_OUT)
        report.write(out)
        print("\n".join(report.annotations()))
        v = report.extra.get("verdict")
        if v:
            print(json.dumps({k: v[k] for k in ("faithfulness", "decidability", "outcome_label",
                                                 "verdict") if k in v}, sort_keys=True))
        print(f"wrote {out}")
    return report.exit_code()
