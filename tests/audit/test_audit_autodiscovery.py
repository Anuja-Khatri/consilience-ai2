"""The AutoDiscovery adapter on the SYNTHETIC schema fixtures."""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys

import pytest

from consilience_ai2.audit import audit_path, detect_format, load


def _planted(ad_examples):
    return json.loads((ad_examples / "planted.json").read_text())


def _flagged(node):
    return sorted({c["code"] for c in node["checks"] if c["severity"] in ("error", "warning")})


def test_every_planted_code_found_and_nothing_else(ad_examples):
    data, _ = audit_path(ad_examples / "synthetic_run")
    planted = _planted(ad_examples)
    got = {n["id"]: _flagged(n) for n in data["nodes"]}
    assert set(got) == set(planted)  # root node_1_0 skipped
    for nid, codes in planted.items():
        assert got[nid] == sorted(codes), nid
    assert data["format"] == "autodiscovery" and data["n_nodes"] == len(planted)


def test_node_files_and_nodes_all_agree(ad_examples, tmp_path):
    d1, _ = audit_path(ad_examples / "synthetic_run")
    d2, _ = audit_path(ad_examples / "synthetic_run" / "mcts_nodes_all.json",
                       metadata=ad_examples / "synthetic_run" / "dataset_metadata.json")
    assert [(n["id"], n["verdict"], n["codes"]) for n in d1["nodes"]] == \
        [(n["id"], n["verdict"], n["codes"]) for n in d2["nodes"]]


def test_hosted_results(ad_examples):
    assert detect_format(ad_examples / "synthetic_hosted") == "autodiscovery"
    data, _ = audit_path(ad_examples / "synthetic_hosted")
    got = {n["id"]: _flagged(n) for n in data["nodes"]}
    planted = _planted(ad_examples)
    for nid in got:
        expect = set(planted[nid]) - {"A3"}  # no metadata with a hosted export
        assert set(got[nid]) == expect, nid
    assert data["run"] == "synthetic-hosted-run"


def test_metadata_from_args_and_llm_review_hashed(ad_examples):
    r = load(ad_examples / "synthetic_run")
    assert r.nodes[0].columns and "bmi" in r.nodes[0].columns
    data, _ = audit_path(ad_examples / "synthetic_run")
    n0 = data["nodes"][0]
    assert n0["llm_validity_check"]["success"] is True
    assert len(n0["llm_validity_check"]["text_sha256"]) == 64


def test_fixture_keys_match_released_schema(ad_examples):
    spec = importlib.util.spec_from_file_location("mk", ad_examples / "make_fixtures.py")
    mk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mk)
    for f in sorted((ad_examples / "synthetic_run").glob("mcts_node_*.json")):
        d = json.loads(f.read_text())
        assert list(d) == mk.NODE_KEYS, f.name
        if d["prior"] is not None:
            assert list(d["prior"]) == mk.BELIEF_KEYS
            assert list(d["experiment_plan"]) == mk.PLAN_KEYS
    hosted = json.loads((ad_examples / "synthetic_hosted" / "results.json").read_text())
    for e in hosted["experiments"]:
        assert list(e) == mk.EXPERIMENT_MODEL_KEYS


def test_fixture_keys_match_fetched_source(ad_examples):
    """When asta-autodiscovery is fetched, read MCTSNode.to_dict's keys from its source."""
    from consilience_ai2.fetch import FetchError, require

    try:
        root = require("asta-autodiscovery")
    except FetchError:
        pytest.skip("asta-autodiscovery not fetched")
    src = (root / "packages/autodiscovery/src/autodiscovery/mcts.py").read_text()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "to_dict")
    ret = next(n for n in ast.walk(fn) if isinstance(n, ast.Return))
    keys = [k.value for k in ret.value.keys]
    d = json.loads((ad_examples / "synthetic_run" / "mcts_node_2_0.json").read_text())
    assert list(d) == keys


def test_fixtures_regenerate_byte_identical(ad_examples, tmp_path):
    before = {p: p.read_bytes() for p in sorted(ad_examples.rglob("*.json"))}
    subprocess.run([sys.executable, str(ad_examples / "make_fixtures.py")], check=True)
    after = {p: p.read_bytes() for p in sorted(ad_examples.rglob("*.json"))}
    assert before == after
