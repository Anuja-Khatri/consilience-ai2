"""The DiscoveryBench scan on a synthetic task (no fetched data needed)."""

from __future__ import annotations

import json

import numpy as np

from consilience_ai2.audit.discoverybench import (
    column_type,
    load_task,
    pair_test,
    permuted_target,
    read_csv,
    scan_task,
)


def make_task(tmp_path, n=200, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    noise = rng.normal(size=n)
    grp = rng.choice(["a", "b", "c"], size=n)
    flag = rng.choice(["yes", "no"], size=n)
    y = 2 * x + 0.1 * rng.normal(size=n)
    d = tmp_path / "toy_0_0"
    d.mkdir()
    rows = ["x,noise,grp,flag,const,y"] + [
        f"{x[i]:.4f},{noise[i]:.4f},{grp[i]},{flag[i]},1,{y[i]:.4f}" for i in range(n)]
    (d / "data.csv").write_text("\n".join(rows) + "\n")
    meta = {"id": 0, "domain": "toy", "datasets": [{"name": "data.csv", "columns": [
        {"name": c, "description": c} for c in ["x", "noise", "grp", "flag", "const", "y"]]}],
        "queries": [{"qid": 1, "question": "q", "target_col": "y", "relevant_cols": ["x", "y"],
                     "true_hypothesis_expr": "2*x"}]}
    (d / "metadata_0.json").write_text(json.dumps(meta))
    return load_task(d / "metadata_0.json", "train")


def test_column_types():
    assert column_type(["1", "2", "3"]) == "numeric"
    assert column_type(["a", "b", "a"]) == "binary"
    assert column_type(["a", "b", "c", "a", "b", "c"]) == "categorical"
    assert column_type(["a", "b", "c", "d"]) == "identifier"
    assert column_type(["1", "1", ""]) == "constant"


def test_tests_per_type():
    num = [str(i) for i in range(30)]
    assert pair_test(num, "numeric", num, "numeric")[0] == "spearman"
    b = ["u", "v"] * 15
    assert pair_test(b, "binary", num, "numeric")[0] == "point-biserial"
    c = ["p", "q", "r"] * 10
    assert pair_test(c, "categorical", num, "numeric")[0] == "kruskal-wallis"
    assert pair_test(c, "categorical", b, "binary")[0] == "chi-square"
    assert pair_test(["1"] * 30, "constant", num, "numeric")[0] is None


def test_scan_finds_gold_and_bh_within_task(tmp_path):
    task = make_task(tmp_path)
    assert task.has_structured_gold and task.target == "y"
    sc = scan_task(task, read_csv(task.csv_path))
    by = {t.column: t for t in sc.tests}
    assert by["x"].kind == "gold" and by["x"].p < 1e-10 and by["x"].q < 0.05
    assert by["noise"].kind == "distractor" and by["const"].p is None
    assert all(t.q is None or t.q >= t.p for t in sc.tests)


def test_permuted_target_is_deterministic(tmp_path):
    task = make_task(tmp_path)
    data = read_csv(task.csv_path)
    a = permuted_target(data["y"], 7)
    assert a == permuted_target(data["y"], 7) and sorted(a) == sorted(data["y"])
    sc = scan_task(task, data, target_values=a)
    assert by_q(sc) > 0.05


def by_q(sc):
    return min(t.q for t in sc.tests if t.q is not None)
