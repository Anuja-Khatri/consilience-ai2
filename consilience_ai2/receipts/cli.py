"""``consilience-ai2 receipts``: evidence receipts for Asta workspaces.

    consilience-ai2 receipts check <workspace_dir> [--sources DIR|paperstore.json|index.json ...]
                                   [--json OUT] [--no-annotations] [--fail-on-warnings]
                                   [--rules v0.1|v0.2] [--with-w2]

W2 (certainty upgrade) is opt-in with ``--with-w2``: on a hand-checked sample only about
a third of its flags were real overreach. W1 (number overreach) is on by default, as a
warning; about half of its flags were real.

Prints one GitHub annotation line per error or warning finding (info receipts go to the
JSON report only, unless ``--all-annotations``), then a one-line summary on stderr.
Exit code: 0 when there is no error finding, 1 on any error (any E code, including
``E6 NOT_FOUND``), 2 on a usage error. ``--fail-on-warnings`` also fails on W1 (and W2 when on).
"""

from __future__ import annotations

import argparse
import sys

from consilience_ai2.receipts.claims import DEFAULT_RULES, RULE_SETS
from consilience_ai2.receipts.sources import SourceError
from consilience_ai2.receipts.workspace import check_workspace


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "receipts",
        help="evidence receipts: check an Asta workspace's .ev evidence",
        description=(
            "Deterministic checks of an Asta workspace's evidence: unknown keys (E1), "
            "missing quotes (E2), citations missing from the bibliography (E3), orphaned "
            "entries (E4), provenance format (E5), quotes verbatim in local source text "
            "(E6), number overreach (W1) and, with --with-w2, certainty upgrades (W2)."
        ),
    )
    sub = p.add_subparsers(dest="receipts_command", metavar="<subcommand>")
    c = sub.add_parser("check", help="check a workspace directory",
                       description="Check a workspace directory and report findings.")
    c.add_argument("workspace", help="the workspace directory (holds _quarto.yml or evidence.yml)")
    c.add_argument("--sources", metavar="DIR|FILE", action="append",
                   help="local source text for E6: a directory of <cite>.txt / <corpus_id>.txt "
                        "files, an Asta paperstore.json, or an AutoDiscovery index.json; "
                        "repeat to try several in order")
    c.add_argument("--json", metavar="OUT", help="write the version-1 JSON report here")
    c.add_argument("--no-annotations", action="store_true",
                   help="do not print GitHub annotation lines")
    c.add_argument("--all-annotations", action="store_true",
                   help="also print info findings (E6 FOUND / UNCHECKABLE receipts)")
    c.add_argument("--fail-on-warnings", action="store_true",
                   help="exit 1 on W1 (and W2) warnings as well as errors")
    c.add_argument("--with-w2", action="store_true",
                   help="also run W2, the certainty-upgrade check (off by default: on a "
                        "hand-checked sample only about a third of its flags were real "
                        "overreach)")
    c.add_argument("--rules", choices=RULE_SETS, default=DEFAULT_RULES,
                   help=f"W1/W2 rule version (default {DEFAULT_RULES}; v0.1 is the frozen "
                        "rule set of the preregistered SciArena test)")
    c.set_defaults(func=run_check)
    p.set_defaults(func=lambda args: (p.print_help(sys.stderr), 2)[1])


def run_check(args: argparse.Namespace) -> int:
    try:
        report = check_workspace(args.workspace, args.sources, args.rules,
                                 with_w2=args.with_w2)
    except SourceError as exc:
        print(f"receipts: {exc}", file=sys.stderr)
        return 2
    if args.json:
        report.write(args.json)
    if not args.no_annotations:
        for f in report.sorted_findings():
            if f.severity != "info" or args.all_annotations:
                print(f.to_annotation())
    s = report.summary()
    print(f"receipts: {report.extra.get('checked_spans', 0)} spans, "
          f"{report.extra.get('entries', 0)} entries; "
          f"{s['by_severity']['error']} errors, {s['by_severity']['warning']} warnings, "
          f"{s['by_severity']['info']} receipts", file=sys.stderr)
    fail_on = ("error", "warning") if args.fail_on_warnings else ("error",)
    return report.exit_code(fail_on=fail_on)
