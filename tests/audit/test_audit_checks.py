"""Every check in both directions, on small synthetic nodes."""

from __future__ import annotations

LOAD = 'import pandas as pd\nfrom scipy import stats\ndf = pd.read_csv("d.csv")\n'


# A1 ---------------------------------------------------------------------------------

def test_a1_supported_number_passes(aud):
    n = aud.make_node(analysis="r = 0.24 (p = 0.001)", output="r = 0.2381, p = 0.001\n")
    d = aud.run_nodes(n)
    assert "A1" not in aud.codes_of(d, n.id) and "A1" in aud.info_codes(d, n.id)


def test_a1_unsupported_number_refuses_with_receipt(aud):
    n = aud.make_node(analysis="r = 0.42 (p = 0.001)", output="r = 0.24, p = 0.001\n")
    d = aud.run_nodes(n)
    node = d["nodes"][0]
    assert node["verdict"] == "refuse"
    a1 = [c for c in node["checks"] if c["code"] == "A1" and c["severity"] == "error"]
    assert len(a1) == 1
    assert a1[0]["span"] == "0.42" and a1[0]["field"] == "analysis"
    assert a1[0]["offset"] == 4 and a1[0]["end"] == 8 and len(a1[0]["sha256"]) == 64


def test_a1_percent_and_scale_and_bounds(aud):
    n = aud.make_node(analysis="accuracy 24.0%, p < 0.001", output="accuracy: 0.24\np = 0.0002\n")
    assert "A1" not in aud.codes_of(aud.run_nodes(n), n.id)


def test_a1_more_precision_than_printed_is_flagged(aud):
    n = aud.make_node(analysis="mean 0.343", output="mean 0.34\n")
    assert "A1" in aud.codes_of(aud.run_nodes(n), n.id)


def test_a1_code_constant_counts_as_support(aud):
    n = aud.make_node(analysis="threshold 0.75 used; r = 0.3 (p = 0.01)", output="r = 0.30 p = 0.01",
                  code="THRESHOLD = 0.75\n")
    assert "A1" not in aud.codes_of(aud.run_nodes(n), n.id)


# A2 ---------------------------------------------------------------------------------

def test_a2_stated_n_printed_passes(aud):
    n = aud.make_node(analysis="Across 1200 respondents r = 0.3 (p = 0.01).",
                  output="n = 1200\nr = 0.3, p = 0.01")
    d = aud.run_nodes(n)
    assert "A2" not in aud.codes_of(d, n.id) and "A2" in aud.info_codes(d, n.id)


def test_a2_plan_2000_code_and_output_20_flags(aud):
    n = aud.make_node(plan="Sample 2000 respondents.", analysis="rho = 0.5, p = 0.01",
                  output="n = 20\nrho = 0.5, p = 0.01", code=LOAD + "N = 20\nsub = df.sample(N)\n")
    assert "A2" in aud.codes_of(aud.run_nodes(n), n.id)


# A3 ---------------------------------------------------------------------------------

def test_a3_known_columns_pass(aud):
    n = aud.make_node(analysis="r = 0.3, p = 0.01", output="r = 0.3, p = 0.01",
                  code=LOAD + 'df2 = df[df["age"] > 30]\nx = df2["income"]\n',
                  columns={"age", "income"})
    d = aud.run_nodes(n)
    assert "A3" not in aud.codes_of(d, n.id) and "A3" in aud.info_codes(d, n.id)


def test_a3_unknown_column_refuses(aud):
    n = aud.make_node(analysis="r = 0.3, p = 0.01", output="r = 0.3, p = 0.01",
                  code=LOAD + 'x = df["household_size"]\ndf["new_col"] = 1\ny = df["new_col"]\n',
                  columns={"age"})
    d = aud.run_nodes(n)
    a3 = [c for c in d["nodes"][0]["checks"] if c["code"] == "A3" and c["severity"] == "error"]
    assert [c["details"]["column"] for c in a3] == ["household_size"]  # created column is fine
    assert a3[0]["line"] == 4 and d["nodes"][0]["verdict"] == "refuse"


def test_a3_groupby_result_labels_are_not_columns(aud):
    n = aud.make_node(analysis="x", output="y", columns={"smoker", "sleep"},
                  code=LOAD + 'm = df.groupby("smoker")["sleep"].mean()\nprint(m["no"])\n')
    assert "A3" not in aud.codes_of(aud.run_nodes(n), n.id)


def test_a3_needs_metadata(aud):
    n = aud.make_node(analysis="x", output="y", code=LOAD + 'z = df["anything"]\n')
    assert "A3" in aud.run_nodes(n)["nodes"][0]["not_applicable"]


# A4 ---------------------------------------------------------------------------------

def test_a4_test_printed_passes(aud):
    n = aud.make_node(analysis="Significantly higher (p = 0.01).", output="t = 2.9, p = 0.01")
    d = aud.run_nodes(n)
    assert "A4" not in aud.codes_of(d, n.id) and "A4" in aud.info_codes(d, n.id)


def test_a4_significance_without_test_flags(aud):
    n = aud.make_node(analysis="Smokers sleep significantly less (6.1 vs 7.4).",
                  output="yes 6.1\nno 7.4\n")
    assert "A4" in aud.codes_of(aud.run_nodes(n), n.id)


# A5 ---------------------------------------------------------------------------------

def test_a5_bh_across_run_flags_surprising_node_and_reports_coverage(aud):
    sig = aud.make_node("node_2_0", analysis="r = 0.5 (p = 0.001)", output="r = 0.5, p = 0.001")
    marginal = aud.make_node("node_2_1", analysis="effect (p = 0.04)",
                         output="p = 0.04\np = 0.3\np = 0.5\np = 0.7\np = 0.9")
    nop = aud.make_node("node_2_2", analysis="nothing", output="no numbers", surprising=False)
    d = aud.run_nodes(sig, marginal, nop)
    assert "A5" not in aud.codes_of(d, "node_2_0")
    assert "A5" in aud.codes_of(d, "node_2_1")
    q = {n["id"]: n["q_value"] for n in d["nodes"]}
    assert q["node_2_0"] < 0.05 < q["node_2_1"] and q["node_2_2"] is None
    assert d["n_with_pvalue"] == 2 and d["parse_coverage"]["nodes_checkable"] == 3
    assert d["parse_coverage"]["pvalues"] == 6


def test_a5_not_surprising_is_info_only(aud):
    n = aud.make_node(analysis="p = 0.4", output="p = 0.4", surprising=False)
    d = aud.run_nodes(n)
    assert "A5" not in aud.codes_of(d, n.id) and "A5" in aud.info_codes(d, n.id)


# A6 ---------------------------------------------------------------------------------

def test_a6_underpowered_surprising_null_flags(aud):
    n = aud.make_node(analysis="No association (rho = 0.05, p = 0.79, n = 30).",
                  output="n = 30\nrho = 0.05, p = 0.79", prior=0.8, posterior=0.3)
    d = aud.run_nodes(n)
    a6 = [c for c in d["nodes"][0]["checks"] if c["code"] == "A6"]
    assert a6 and a6[0]["severity"] == "warning"
    assert a6[0]["details"]["n"] == 30 and a6[0]["details"]["mde_d"] > 0.5
    assert "A5" not in aud.codes_of(d, n.id)  # a null's large q is not an A5 flag


def test_a6_well_powered_null_is_info(aud):
    n = aud.make_node(analysis="No association (rho = 0.01, p = 0.7).",
                  output="n = 5000\nrho = 0.01, p = 0.7", prior=0.8, posterior=0.3)
    d = aud.run_nodes(n)
    assert "A6" not in aud.codes_of(d, n.id) and "A6" in aud.info_codes(d, n.id)


# A7 ---------------------------------------------------------------------------------

def test_a7_effect_size_present_passes(aud):
    n = aud.make_node(analysis="Higher bmi in smokers (Cohen's d = 0.4, p = 0.001).",
                  output="d = 0.4, p = 0.001")
    d = aud.run_nodes(n)
    assert "A7" not in aud.codes_of(d, n.id) and "A7" in aud.info_codes(d, n.id)


def test_a7_missing_effect_size_flags(aud):
    n = aud.make_node(analysis="Smokers have a significantly higher bmi (t = 3.2, p = 0.001).",
                  output="t = 3.2, p = 0.001")
    assert "A7" in aud.codes_of(aud.run_nodes(n), n.id)


# R1 ---------------------------------------------------------------------------------

def test_r1_random_only_flags(aud):
    n = aud.make_node(analysis="The agent outperforms a random baseline (0.34 vs 0.17, p = 0.001).",
                  output="0.34 0.17 p = 0.001")
    assert "R1" in aud.codes_of(aud.run_nodes(n), n.id)


def test_r1_other_comparator_passes(aud):
    n = aud.make_node(analysis="We compare three agents: random, ReAct and ours. Ours outperforms "
                  "the ReAct baseline and a random agent (p = 0.01).", output="p = 0.01")
    d = aud.run_nodes(n)
    assert "R1" not in aud.codes_of(d, n.id) and "R1" in aud.info_codes(d, n.id)


# R2 ---------------------------------------------------------------------------------

def test_r2_flip_flags(aud):
    n = aud.make_node(analysis="x", output="y", reruns=["support", "refute", "inconclusive"])
    assert "R2" in aud.codes_of(aud.run_nodes(n), n.id)


def test_r2_consistent_passes_and_needs_reruns(aud):
    n = aud.make_node(analysis="x", output="y", reruns=["support", "support", "inconclusive"])
    assert "R2" in aud.info_codes(aud.run_nodes(n), n.id)
    m = aud.make_node(analysis="x", output="y")
    assert "R2" in aud.run_nodes(m)["nodes"][0]["not_applicable"]


# R3 ---------------------------------------------------------------------------------

def test_r3_small_n_flags(aud):
    n = aud.make_node(analysis="The planner significantly outperforms (p = 0.01).",
                  output="n = 20\np = 0.01")
    d = aud.run_nodes(n)
    r3 = [c for c in d["nodes"][0]["checks"] if c["code"] == "R3"]
    assert r3[0]["severity"] == "warning" and r3[0]["details"]["floor"] == 25


def test_r3_large_n_passes(aud):
    n = aud.make_node(analysis="The planner significantly outperforms (p = 0.01).",
                  output="n = 200\np = 0.01")
    d = aud.run_nodes(n)
    assert "R3" not in aud.codes_of(d, n.id) and "R3" in aud.info_codes(d, n.id)


# R4 ---------------------------------------------------------------------------------

def test_r4_hardcoded_result_flags(aud):
    n = aud.make_node(analysis="Accuracy is 0.87.", output="accuracy = 0.87",
                  code="accuracy = 0.87\nprint(f'accuracy = {accuracy}')\n")
    d = aud.run_nodes(n)
    r4 = [c for c in d["nodes"][0]["checks"] if c["code"] == "R4"]
    assert r4 and r4[0]["details"]["code_line"] == 1


def test_r4_computed_result_passes(aud):
    n = aud.make_node(analysis="Accuracy is 0.87.", output="accuracy = 0.87",
                  code="import numpy as np\naccuracy = np.mean([1, 0])\n"
                  "print(f'accuracy = {accuracy:.2f}')\nTHRESHOLD = 0.5\n")
    assert "R4" not in aud.codes_of(aud.run_nodes(n), n.id)


# R5 ---------------------------------------------------------------------------------

def test_r5_unused_component_flags(aud):
    code = (LOAD + "def build_graph(d):\n    g = d.copy()\n    return g\n\n"
            "graph = build_graph(df)\nr = stats.pearsonr(df['a'], df['b'])\nprint(r)\n")
    n = aud.make_node(analysis="r = 0.3", output="r = 0.3", code=code)
    d = aud.run_nodes(n)
    r5 = [c for c in d["nodes"][0]["checks"] if c["code"] == "R5" and c["severity"] == "error"]
    assert [c["details"]["component"] for c in r5] == ["build_graph"]


def test_r5_used_component_passes(aud):
    code = (LOAD + "def build_graph(d):\n    g = d.copy()\n    return g\n\n"
            "graph = build_graph(df)\nr = stats.pearsonr(graph['a'], graph['b'])\nprint(r)\n")
    n = aud.make_node(analysis="r = 0.3", output="r = 0.3", code=code)
    d = aud.run_nodes(n)
    assert "R5" not in aud.codes_of(d, n.id) and "R5" in aud.info_codes(d, n.id)


def test_r5_mutation_through_argument_counts_as_use(aud):
    code = ("def enrich(d):\n    d['z'] = 1\n\nrows = {}\nenrich(rows)\nprint(rows)\n")
    n = aud.make_node(analysis="x", output="y", code=code)
    assert "R5" not in aud.codes_of(aud.run_nodes(n), n.id)


def test_r5_dynamic_code_is_uncheckable_not_flagged(aud):
    code = "def f():\n    return 1\n\nx = f()\nprint(eval('x'))\n"
    n = aud.make_node(analysis="x", output="y", code=code)
    d = aud.run_nodes(n)
    r5 = [c for c in d["nodes"][0]["checks"] if c["code"] == "R5"]
    assert r5 and r5[0]["severity"] == "info" and "not decidable" in r5[0]["message"]


# verdicts ---------------------------------------------------------------------------

def test_uncheckable_node_is_refused(aud):
    n = aud.make_node(analysis="x", output=None)
    d = aud.run_nodes(n)
    assert d["nodes"][0]["verdict"] == "refuse"
    assert aud.codes_of(d, n.id) == {"U1"}


def test_clean_node_passes_and_llm_text_is_hashed(aud):
    n = aud.make_node(analysis="Exercise is negatively correlated with bmi (rho = -0.31, "
                  "p = 1.2e-27, n = 1200).", output="n = 1200\nrho = -0.31, p = 1.2e-27",
                  review="Looks right.", success=True)
    d = aud.run_nodes(n)
    node = d["nodes"][0]
    assert node["verdict"] == "pass", node["codes"]
    assert node["llm_validity_check"]["success"] is True
    assert len(node["llm_validity_check"]["text_sha256"]) == 64
