"""Run `auto-discovery` with a deterministic audit attached to every saved node.

EXAMPLE ONLY: this is not a patch to AutoDiscovery and is not part of the package. It
follows the pattern of asta-plugins' ``run_relaxed.py``: it wraps AutoDiscovery's own
functions from outside, at run time, without modifying the installed package.

    "$(uv tool dir)/asta-autodiscovery/bin/python" -I run_with_audit.py <auto-discovery args>

It must run on AutoDiscovery's own Python (where ``autodiscovery`` is importable) with
``consilience-ai2`` installed there too
(``pip install "git+https://github.com/Anuja-Khatri/consilience-ai2"``).

What it does: ``autodiscovery.mcts_utils.save_nodes`` turns the MCTS nodes into dicts
(``MCTSNode.to_dict``) and writes ``mcts_nodes.json``, ``mcts_nodes_all.json`` and the
CSV. The wrapper converts the nodes to dicts first, runs the consilience-ai2 audit on
them, adds a ``deterministic_checks`` field to each dict (verdict, codes, q value, the
SHA-256 of the reviewer's "Validity Check" text), and then calls the original
``save_nodes`` with those dicts. The reviewer's pass flag and text are left untouched.
``MCTSNode.init_from_dict`` ignores unknown keys, so the saved files still load.

The simpler, fully supported hook is the post-run command:

    consilience-ai2 audit run <out_dir> --metadata <dataset_metadata.json>

Tested only against the synthetic fixtures in examples/audit/autodiscovery/ (no
AutoDiscovery run was made); it checks that the function it wraps exists and stops if not.
"""

from __future__ import annotations

import sys

import autodiscovery.mcts_utils as mcts_utils
import autodiscovery.run as run

from consilience_ai2.audit.adapters import _ad_node, load_metadata
from consilience_ai2.audit.engine import audit
from consilience_ai2.audit.model import Run
from consilience_ai2.core.hashing import canonical_json, sha256_text

_save_nodes = getattr(mcts_utils, "save_nodes", None)
if _save_nodes is None:
    raise SystemExit("run_with_audit: autodiscovery.mcts_utils.save_nodes not found; "
                     "this AutoDiscovery version is not supported")


def _metadata_path(argv: list[str]) -> str | None:
    for i, a in enumerate(argv):
        if a == "--dataset_metadata" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--dataset_metadata="):
            return a.split("=", 1)[1]
    return None


_META = _metadata_path(sys.argv[1:])
_COLUMNS = None
if _META and not _META.startswith("s3"):
    try:
        _COLUMNS, _NAME, _SHA = load_metadata(_META)
    except OSError:
        _COLUMNS = None


def _as_dicts(nodes_dict_or_list) -> list[dict]:
    from autodiscovery.mcts import MCTSNode

    if isinstance(nodes_dict_or_list, dict):
        out = []
        for level, nodes in nodes_dict_or_list.items():
            if level == 0:
                continue
            out.extend(n.to_dict() for n in nodes)
        return out
    return [n.to_dict() if isinstance(n, MCTSNode) else n for n in nodes_dict_or_list]


def save_nodes(nodes_dict_or_list, log_dirname, **kwargs):
    dicts = _as_dicts(nodes_dict_or_list)
    r = Run(run=str(log_dirname), format="autodiscovery")
    for d in dicts:
        if d.get("hypothesis") and d.get("id") and not str(d["id"]).startswith("node_1_"):
            text = canonical_json(d)
            r.nodes.append(_ad_node(d, f"{d['id']}.json", sha256_text(text), False,
                                    _COLUMNS, _META))
    data, _report = audit(r)
    by_id = {n["id"]: n for n in data["nodes"]}
    for d in dicts:
        n = by_id.get(str(d.get("id")))
        if n is not None:
            d["deterministic_checks"] = {
                "tool": data["tool"], "tool_version": data["tool_version"],
                "rules_version": data["rules_version"], "verdict": n["verdict"],
                "verdict_level": n["verdict_level"], "notes": n["notes"],
                "codes": n["codes"], "q_value": n["q_value"],
                "llm_validity_check": n["llm_validity_check"],
                "checks": [c for c in n["checks"] if c["severity"] != "info"],
            }
    return _save_nodes(dicts, log_dirname, **kwargs)


# run.py imports save_nodes by name, so patch both the module that defines it and the one
# that calls it.
mcts_utils.save_nodes = save_nodes
run.save_nodes = save_nodes

if __name__ == "__main__":
    from autodiscovery.easy import cli_main

    print("save_nodes: consilience-ai2 deterministic audit attached", file=sys.stderr)
    cli_main(sys.argv[1:])
