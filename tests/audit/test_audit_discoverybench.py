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


# derived gold (rules v0.2) ------------------------------------------------------------

def _nl_task(tmp_path, question, hypothesis=""):
    from consilience_ai2.audit.discoverybench import Task
    return Task("t", "train", tmp_path / "m.json", tmp_path / "data.csv", None, [],
                ["conflict_count", "conflict_count_last_decade", "number_of_ziggurats",
                 "conflict_ratio", "age"], False, question=question, hypothesis=hypothesis)


def test_mentions_are_whole_words_and_longest_first(tmp_path):
    from consilience_ai2.audit.discoverybench import mentions
    cols = ["conflict_count", "conflict_count_last_decade", "age"]
    got = [c for _, c in mentions("How does the conflict count last decade relate to "
                                  "average income?", cols)]
    assert got == ["conflict_count_last_decade"]  # not conflict_count; "age" not in "average"
    got = [c for _, c in mentions("Conflict-count and AGE.", cols)]
    assert got == ["conflict_count", "age"]


def test_derive_gold_target_is_first_in_question(tmp_path):
    from consilience_ai2.audit.discoverybench import derive_gold, with_derived_gold
    t = _nl_task(tmp_path, "Is the conflict ratio related to the number of ziggurats?",
                 "Cities with more number of ziggurats and a higher conflict count have ...")
    dg = derive_gold(t)
    assert dg.usable and dg.target == "conflict_ratio"
    assert dg.relevant == ["number_of_ziggurats", "conflict_count"]
    td = with_derived_gold(t, dg)
    assert td.target == "conflict_ratio" and not td.has_structured_gold
    assert set(td.relevant) == {"conflict_ratio", "number_of_ziggurats", "conflict_count"}


def test_derive_gold_unusable_without_two_columns(tmp_path):
    from consilience_ai2.audit.discoverybench import derive_gold
    assert not derive_gold(_nl_task(tmp_path, "Does the conflict ratio change?")).usable
    assert not derive_gold(_nl_task(tmp_path, "What explains city growth?")).usable
    # hypothesis only: target is its first mention
    dg = derive_gold(_nl_task(tmp_path, "What explains it?", "age drives conflict ratio"))
    assert dg.target == "age" and dg.relevant == ["conflict_ratio"]
