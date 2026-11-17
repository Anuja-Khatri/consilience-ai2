"""``consilience-ai2 audit run <dir>``: the experiment audit as a post-run command.

    consilience-ai2 audit run OUT_DIR [--format autodiscovery|codescientist]
                                      [--metadata FILE] [--json OUT]

Writes ``OUT_DIR/validity_audit.json`` (or ``--json OUT``), prints one line per node and
GitHub annotation lines for errors and warnings. Exit code 0 when no node has an
error-severity finding, 1 otherwise (or on unreadable input), 2 on a usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from consilience_ai2.audit import load
from consilience_ai2.audit.engine import audit


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "audit", help="deterministic audit of agent-run experiments (AutoDiscovery, CodeScientist)",
        description="Deterministic, receipt-backed audit of agent-run experiments. Runs "
        "beside AutoDiscovery's language-model Validity Check; its text is hashed, not judged.")
    sub = p.add_subparsers(dest="audit_command", metavar="<subcommand>")
    r = sub.add_parser("run", help="audit a run directory",
                       description="Audit an AutoDiscovery output directory (mcts_node_*.json, "
                       "mcts_nodes_all.json or a hosted results.json) or a CodeScientist "
                       "experiment directory.")
    r.add_argument("path", help="run directory (or an AutoDiscovery node/results JSON file)")
    r.add_argument("--format", choices=("autodiscovery", "codescientist"), default=None,
                   help="input format (detected when omitted)")
    r.add_argument("--metadata", metavar="FILE", default=None,
                   help="dataset metadata JSON (AutoDiscovery --dataset_metadata), for A3")
    r.add_argument("--json", metavar="OUT", default=None,
                   help="where to write validity_audit.json (default: <dir>/validity_audit.json)")
    r.set_defaults(func=run)
    p.set_defaults(func=lambda args: (p.print_help(sys.stderr), 2)[1])


def run(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"audit: {path} does not exist", file=sys.stderr)
        return 1
    try:
        r = load(path, format=args.format, metadata=args.metadata)
    except (OSError, ValueError) as exc:
        print(f"audit: cannot read {path}: {exc}", file=sys.stderr)
        return 1
    data, report = audit(r)
    out = Path(args.json) if args.json else (path if path.is_dir() else path.parent) / \
        "validity_audit.json"
    report.write(out)
    for n in data["nodes"]:
        q = "" if n["q_value"] is None else f" q={n['q_value']:.3g}"
        print(f"{n['id']}: {n['verdict']}{q} {' '.join(n['codes'])}".rstrip())
    for line in report.annotations():
        if not line.startswith("::notice"):
            print(line)
    v = data["verdicts"]
    print(f"audit: {data['n_nodes']} nodes, {v['pass']} pass, {v['flag']} flag, "
          f"{v['refuse']} refuse; p values parsed for {data['n_with_pvalue']}; wrote {out}")
    return report.exit_code()
