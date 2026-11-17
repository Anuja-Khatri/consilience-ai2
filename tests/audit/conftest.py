"""Fixtures for the C2 audit tests. All synthetic; no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consilience_ai2.audit.engine import audit
from consilience_ai2.audit.model import CLAIM, CODE, CONTEXT, EVIDENCE, Node, Run, TextField
from consilience_ai2.core.hashing import sha256_text

REPO = Path(__file__).resolve().parents[2]
AD_EXAMPLES = REPO / "examples" / "audit" / "autodiscovery"


def make_node(nid: str = "node_2_0", *, analysis: str | None = None, output: str | None = None,
              code: str | None = None, hypothesis: str | None = None, plan: str | None = None,
              surprising: bool | None = True, prior: float | None = None,
              posterior: float | None = None, columns: set[str] | None = None,
              reruns: list[str] | None = None, results=None, review: str | None = None,
              success: bool | None = None) -> Node:
    n = Node(id=nid, surprising=surprising, prior_mean=prior, posterior_mean=posterior,
             columns=columns, columns_source="meta.json" if columns is not None else None,
             reruns=reruns, success=success, review_text=review)

    def add(name, kind, text):
        if text is not None:
            n.fields.append(TextField(name, kind, text, f"{nid}.json", sha256_text(text),
                                      in_json=True))

    add("hypothesis", CONTEXT, hypothesis)
    add("experiment_plan", CONTEXT, plan)
    add("code", CODE, code)
    add("code_output", EVIDENCE, output)
    add("analysis", CLAIM, analysis)
    if results is not None:
        add("results", EVIDENCE, json.dumps(results))
        n.results = results
    return n


def run_nodes(*nodes: Node) -> dict:
    data, _ = audit(Run(run="t", format="test", nodes=list(nodes)))
    return data


def codes_of(data: dict, nid: str, severities=("error", "warning")) -> set[str]:
    n = next(x for x in data["nodes"] if x["id"] == nid)
    return {c["code"] for c in n["checks"] if c["severity"] in severities}


def info_codes(data: dict, nid: str) -> set[str]:
    return codes_of(data, nid, ("info",))


@pytest.fixture
def node_factory():
    return make_node


@pytest.fixture
def ad_examples() -> Path:
    return AD_EXAMPLES


@pytest.fixture
def aud():
    """The helpers above as one fixture (pytest's importlib mode cannot import conftest)."""
    import types
    return types.SimpleNamespace(make_node=make_node, run_nodes=run_nodes, codes_of=codes_of,
                                 info_codes=info_codes)
