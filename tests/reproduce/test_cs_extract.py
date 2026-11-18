"""v0.2 extraction of CodeScientist run outputs (``analyses/reproduce/cs_extract.py``):
tolerant parsing, bootstrap blocks in results/to_save/log files, the primary-comparison
rule and the classification of runs without a bootstrap block. Synthetic inputs only."""

from __future__ import annotations

import importlib
import io
import json
import math
import sys
import zipfile
from pathlib import Path

import pytest

ANALYSES = Path(__file__).resolve().parents[2] / "analyses" / "reproduce"


def _load(name: str):
    """Import an analysis module by name (the analyses directory is not a package)."""
    if str(ANALYSES) not in sys.path:
        sys.path.insert(0, str(ANALYSES))
    return importlib.import_module(name)


cx = _load("cs_extract")


def boot(mb=0.2, me=0.5, p=0.01, n=20, **extra):
    return {"mean_baseline": mb, "mean_experimental": me, "p_value": p, "dataset_size": n,
            "num_resamples": 10000, **extra}


def js(obj) -> bytes:
    return json.dumps(obj).encode()


# --- tolerant parsing -------------------------------------------------------------------

def test_load_plain_json():
    assert cx.load_tolerant(b'{"a": 1}') == ({"a": 1}, "json")


def test_load_bom_and_cp1252():
    assert cx.load_tolerant(b'\xef\xbb\xbf{"a": 1}') == ({"a": 1}, "json")
    obj, how = cx.load_tolerant('{"name": "caf\xe9"}'.encode("cp1252"))
    assert obj == {"name": "café"} and how == "json"


def test_load_nan_tokens():
    obj, how = cx.load_tolerant(b'{"a": NaN, "b": Infinity}')
    assert how == "json" and math.isnan(obj["a"]) and obj["b"] == math.inf
    obj, how = cx.load_tolerant(b'{"a": nan, "b": -inf}')
    assert how == "repaired" and math.isnan(obj["a"]) and obj["b"] == -math.inf


def test_load_trailing_commas_and_python_literals():
    obj, how = cx.load_tolerant(b'{"a": [1, 2,], "b": {"c": true,},}')
    assert how == "repaired" and obj == {"a": [1, 2], "b": {"c": True}}
    obj, how = cx.load_tolerant(b"{'a': None, 'b': (1, 2), 'c': False}")
    assert how == "repaired" and obj == {"a": None, "b": [1, 2], "c": False}


@pytest.mark.parametrize("data,how", [(b"", "empty"), (b"  \n", "empty"),
                                      (b"{'a': __import__('os')}", "unparseable"),
                                      (b"{'a': 1 + 2}", "unparseable"),
                                      (b"not json", "unparseable"),
                                      (b"\x81\x8d\x8f\x90\x9d", "undecodable")])
def test_load_refuses(data, how):
    assert cx.load_tolerant(data) == (None, how)


def test_literal_executes_nothing():
    with pytest.raises(ValueError):
        cx.literal("print('x')")
    with pytest.raises(ValueError):
        cx.literal("{**{'a': 1}}")


def test_balanced_is_string_aware():
    text = 'Results: {"a": "}{", \'b\': [1, {"c": 2}]} trailing'
    assert cx.balanced(text, text.index("{")) == '{"a": "}{", \'b\': [1, {"c": 2}]}'
    assert cx.balanced("{unclosed", 0) is None
    assert cx.balanced("x{}", 0) is None


# --- blocks -------------------------------------------------------------------------------

def test_file_blocks_paths_and_labels():
    obj = {"comparisons": [{"baseline": "boolean", "experimental": "full", "stats": boot()},
                           {"baseline": "boolean", "experimental": "relational",
                            "stats": boot(p=0.4)}]}
    bl = cx.file_blocks(obj, "results.json")
    assert [b.where for b in bl] == ["comparisons.[0].stats", "comparisons.[1].stats"]
    assert bl[0].label == "comparisons.[boolean,full].stats"
    pre = cx.file_blocks(obj, "results.json", item_names="fields")
    assert pre[0].label == "comparisons.[baseline=boolean,experimental=full].stats"
    ts = cx.file_blocks({"bootstrap_results": boot()}, "to_save/analysis.json")
    assert ts[0].where == "to_save/analysis.json:bootstrap_results"
    assert ts[0].label == "bootstrap_results"


def test_log_blocks_json_python_previous_label_and_last_wins():
    log = [
        {"type": "info", "message": "Bootstrap results: " + json.dumps(boot(p=0.5))},
        {"type": "info", "message": "Comparison random vs agent: " + repr(boot(p=0.0))},
        {"type": "info", "message": "Bootstrap analysis results for LLM vs Simple:"},
        {"type": "info", "message": json.dumps(boot(p=0.9, n=19), indent=2)},
        {"type": "info", "message": "Bootstrap results: " + json.dumps(boot(p=0.2))},
        {"type": "info", "message": "no dict here {broken"},
    ]
    bl = cx.log_blocks(log)
    assert [b.label for b in bl] == ["Bootstrap results", "Comparison random vs agent",
                                     "Bootstrap analysis results for LLM vs Simple"]
    assert bl[0].raw["p_value"] == 0.2          # the later print of the same label wins
    assert bl[2].raw["dataset_size"] == 19      # label taken from the previous message
    assert cx.is_control(bl[1].where) and not cx.is_control(bl[0].where)


def test_log_blocks_identical_numbers_kept_once():
    log = [{"message": "A: " + json.dumps(boot())}, {"message": "B: " + json.dumps(boot())}]
    assert [b.label for b in cx.log_blocks(log)] == ["A"]
    assert cx.log_blocks({"not": "a list"}) == []


# --- the primary-comparison rule ---------------------------------------------------------

def test_tokens():
    assert cx.tokens("bootstrap_vs_no_graph") == {"no", "graph"}
    assert cx.tokens("Statistical analysis results: graphs 2") == {"graph"}
    assert cx.tokens("") == set()


def test_choose_single():
    assert cx.choose_primary(["anything"], "", "") == (0, "single")


def test_choose_by_hypothesis():
    labels = ["bootstrap_hierarchical_react_without_filtering", "bootstrap_vanilla_react"]
    hyp = "LLM-based subgoal filtering improves hierarchical agents."
    assert cx.choose_primary(labels, hyp, "") == (0, "hypothesis")


def test_choose_by_plan_when_hypothesis_ties():
    labels = ["statistics.scores", "statistics.steps"]
    assert cx.choose_primary(labels, "The agent performs better.",
                             "Compare the average score per episode.") == (0, "experiment_plan")


def test_choose_ambiguous_when_tied_everywhere():
    labels = ["conceptnet_vs_baseline", "llm_vs_baseline"]
    hyp = "Knowledge from ConceptNet or an LLM improves performance."
    assert cx.choose_primary(labels, hyp, hyp) == (None, "ambiguous")
    assert cx.choose_primary(["a.[0].stats", "a.[1].stats"], "x", "y") == (None, "ambiguous")


def test_share_scoring_does_not_favour_longer_names():
    # every candidate is fully named in the plan: no choice (as preregistered, the
    # longer name won on the count of its words)
    labels = ["summary.boil", "summary.find-living-thing", "summary.use-thermometer"]
    plan = "Tasks: boil, find-living-thing and use-thermometer."
    assert cx.choose_primary(labels, "", plan) == (None, "ambiguous")
    assert cx.choose_primary(labels, "", plan, scoring="count") == (1, "experiment_plan")


def test_share_scoring_prefers_the_fully_named_candidate():
    labels = ["LLM_vs_Mathematical", "LLM_vs_Simple", "Mathematical_vs_Simple"]
    hyp = "An LLM approach can match traditional mathematical methods."
    assert cx.choose_primary(labels, hyp, "") == (0, "hypothesis")


def test_words_keep_order():
    assert cx.words("Bootstrap results for LLM vs Simple") == ["llm", "simple"]


def test_comparison_key_matches_across_formats():
    assert cx.comparison_key("statistical_tests.LLM_vs_simple") == \
        cx.comparison_key("Bootstrap analysis results for LLM vs Simple")
    assert cx.comparison_key("comparisons.[boolean,full].stats") == \
        cx.comparison_key("bootstrap_comparisons.boolean_vs_full")


def test_comparison_key_keeps_direction():
    assert cx.comparison_key("A_alpha vs B_beta") != cx.comparison_key("B_beta vs A_alpha")
    assert cx.comparison_key("A_alpha vs B_beta", ordered=False) == \
        cx.comparison_key("B_beta vs A_alpha", ordered=False)


# --- other test outputs --------------------------------------------------------------------

def test_other_tests_classified():
    obj = {"correlations": {"jaccard": {"correlation": 0.1, "p_value": 0.6}},
           "full": {"t_statistic": 2.1, "p_value": 0.04, "n": 30},
           "p_only": [{"baseline": "a", "comparison": "b", "p_value": 1.0}],
           "boot": boot()}
    got = dict(cx.other_tests(obj))
    assert got == {"correlations.jaccard": False, "full": True, "p_only.[0]": False}


# --- one run ----------------------------------------------------------------------------------

def test_extract_tier1_unchanged_from_v01():
    files = {"results.json": js({"pilot_mode": "PILOT", "cmp": boot(),
                                 "random_baseline": boot(p=0.0)}),
             "to_save/a.json": js({"other": boot(p=0.9)})}
    ex = cx.extract_run(files)
    assert ex.status == "ok" and ex.tier == "results.json" and ex.basis == "single"
    assert ex.primary.where == "cmp" and [c.where for c in ex.controls] == ["random_baseline"]


def test_extract_falls_to_to_save_then_log():
    files = {"results.json": b"", "to_save/analysis.json": js({"bootstrap_results": boot()}),
             "log.json": js([{"message": "x: " + json.dumps(boot(p=0.7))}])}
    ex = cx.extract_run(files)
    assert ex.status == "ok" and ex.tier == "to_save"
    assert ex.parse["results.json"] == "empty"
    files.pop("to_save/analysis.json")
    ex = cx.extract_run(files)
    assert ex.status == "ok" and ex.tier == "log.json" and ex.primary.label == "x"


def test_extract_only_controls_in_results_moves_on():
    files = {"results.json": js({"random": boot()}),
             "log.json": js([{"message": "Agent vs baseline: " + json.dumps(boot())}])}
    ex = cx.extract_run(files)
    assert ex.tier == "log.json" and ex.status == "ok"


def test_extract_ambiguous_keeps_candidates():
    files = {"results.json": js({"a_vs_b": boot(), "c_vs_d": boot(p=0.3)})}
    ex = cx.extract_run(files, "nothing in common", "")
    assert ex.status == "ambiguous_primary" and len(ex.candidates) == 2 and ex.primary is None


@pytest.mark.parametrize("files,status", [
    ({"results.json": js({"accuracy": {"a": 0.5, "b": 0.7}})}, "no_test_output"),
    ({"results.json": js({"c": {"correlation": 0.3, "p_value": 0.1}})}, "test_output_incomplete"),
    ({"results.json": js({"t": {"t_stat": 2.0, "p": 0.05, "n": 10}})}, "other_test_output"),
    ({"results.json": b""}, "unreadable_results_file"),
    ({"results.json": b"", "to_save/a.json": js({"acc": 0.5})}, "no_test_output"),
])
def test_extract_classifies_runs_without_a_block(files, status):
    assert cx.extract_run(files).status == status


# --- reading a run from the zip (codescientist_reruns) ----------------------------------------

def _zip(entries: dict[str, bytes]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for k, v in entries.items():
            z.writestr(k, v)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def test_run_numbers_v02_reads_the_final_iteration():
    cs = _load("codescientist_reruns")
    pre = "batch/run-20250101-000000/"
    z = _zip({
        pre + "modal-python-1/modal-output/results.json": js({"cmp": boot(p=0.9)}),
        pre + "modal-python-2/modal-output/results.json": b"",
        pre + "modal-python-2/modal-output/to_save/analysis.json":
            js({"pilot_mode": "PILOT", "bootstrap_results": boot(mb=0.1, me=0.4, p=0.02),
                "random_agent": boot(p=0.001)}),
        pre + "report/to_save/analysis.json": js({"x": boot(p=0.5)}),
    })
    num = cs.run_numbers_v02(z, z.namelist(), "", "")
    assert num["status"] == "ok" and num["tier"] == "to_save"
    assert num["path"] == "to_save/analysis.json:bootstrap_results"
    assert num["measurement"]["value"] == pytest.approx(0.3)
    assert num["measurement"]["n"] == 20 and num["pilot_mode"] == "PILOT"
    assert num["control_p"] == 0.001
    # v0.1 reads only results.json of the final iteration: unreadable here
    assert cs.run_numbers(z, z.namelist())["status"] == "unreadable_results_file"


@pytest.mark.parametrize("mb,me,p,expect", [(1.0, 1.0, 1.0, "zero"),    # zero difference
                                             (0.5, 0.4, 0.01, None),     # sign disagrees
                                             (0.2, 0.5, 0.01, "positive"),
                                             (0.5, 0.2, 0.99, "negative")])
def test_zero_or_inconsistent_difference(mb, me, p, expect):
    cs = _load("codescientist_reruns")
    blk = cx.file_blocks({"b": boot(mb=mb, me=me, p=p, n=10)}, "results.json")[0]
    es = cs.numbers_from_block(blk, None)["measurement"].get("effect_size")
    pre = cs.numbers_from_block(blk, None, zero_effect=False)["measurement"]["effect_size"]
    if expect is None:
        assert es is None and pre["value"] > 0      # as preregistered, it was kept
    elif expect == "zero":
        assert es["value"] == 0.0 and pre["value"] < -1   # as preregistered: a large effect
    else:
        assert (es["value"] > 0) == (expect == "positive") and es == pre


def test_extract_rule_prereg_vs_corrected():
    files = {"results.json": js({"summary": {"boil": boot(), "find-living-thing": boot(p=0.3)}})}
    plan = "Run boil and find-living-thing."
    assert cx.extract_run(files, "", plan).status == "ambiguous_primary"
    ex = cx.extract_run(files, "", plan, rule="v0.2-prereg")
    assert ex.status == "ok" and ex.primary.where == "summary.find-living-thing"


def test_build_record_v02_proxy_note():
    cs = _load("codescientist_reruns")
    num = {"status": "ok", "path": "p", "pilot_mode": None, "basis": "hypothesis",
           "measurement": {"quantity": "q", "value": 0.1, "unit": "dimensionless", "n": 5,
                           "p": 0.2}}
    src = {"name": "s", "hypothesis": "h", "ts": "1", "numbers_v02": num}
    rep = {"name": "r", "hypothesis": "h", "ts": "2",
           "numbers_v02": {**num, "path": "other", "basis": "single"}}
    rec = cs.build_record("idea", src, rep, key="numbers_v02")
    assert rec["quantity_mapping"]["relation"] == "proxy"
    assert "v0.2" in rec["quantity_mapping"]["note"]
