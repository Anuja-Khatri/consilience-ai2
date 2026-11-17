#!/usr/bin/env python3
"""Write the SYNTHETIC AutoDiscovery fixtures in this directory.

    python examples/audit/autodiscovery/make_fixtures.py

No real AutoDiscovery run outputs are public, so the audit's AutoDiscovery adapter is
tested on schema-faithful synthetic runs. Every node here is invented. The schema is
copied from the released code (allenai/asta-autodiscovery at commit 30e080f):

- node dicts have exactly the keys of ``MCTSNode.to_dict`` (``mcts.py``), in its order;
- ``prior``/``posterior`` have the keys of ``BeliefTrueFalse.DistributionFormat.to_dict``
  (``beliefs.py``);
- ``experiment_plan`` has the fields of ``ExperimentPlan`` (``structured_outputs.py``);
- files are named and written as ``save_nodes`` / the persistence layer write them
  (``mcts_node_<level>_<idx>.json``, ``mcts_nodes_all.json``, ``indent=2``);
- the hosted export has the fields of ``ExperimentModel`` (``api/runs/models.py``) under
  ``{"run": ..., "experiments": [...]}``.

Each experiment node plants one defect (or none), named in ``PLANTED`` below and in
README.md; tests/audit/test_autodiscovery_fixtures.py checks the audit finds exactly
those. The output is deterministic: the same script writes the same bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / "synthetic_run"
HOSTED = HERE / "synthetic_hosted"
CREATED = "2026-01-01T00:00:00+00:00"  # fixed, synthetic

# MCTSNode.to_dict keys, in order (asta-autodiscovery mcts.py, commit 30e080f)
NODE_KEYS = [
    "id", "success", "parent_id", "creation_idx", "created_at", "time_elapsed", "visits",
    "value", "self_value", "surprising", "belief_change", "normalized_surprisal",
    "kl_divergence", "prior", "posterior", "hypothesis", "experiment_plan", "code",
    "code_output", "analysis", "review", "untried_experiments", "tried_experiments", "query",
    "messages",
]
BELIEF_KEYS = ["_type", "prior_params", "n", "n_true", "n_false", "_empirical_mean", "mean"]
PLAN_KEYS = ["objective", "steps", "deliverables"]
EXPERIMENT_MODEL_KEYS = [
    "experiment_id", "parent_id", "child_ids", "creation_idx", "created_at", "id_in_run",
    "status", "is_surprising", "surprise", "prior", "posterior", "prior_belief",
    "posterior_belief", "runtime_ms", "hypothesis", "analysis", "experiment_plan", "review",
    "code", "code_output", "rich_outputs",
]

COLUMNS = {
    "age": "Respondent age in years",
    "income": "Annual household income in thousands",
    "education_years": "Years of formal education",
    "region": "Region of residence",
    "smoker": "Whether the respondent smokes (yes/no)",
    "bmi": "Body mass index",
    "sleep_hours": "Average nightly sleep in hours",
    "exercise_days": "Days per week with at least 30 minutes of exercise",
}

LOAD = 'import pandas as pd\nfrom scipy import stats\n\ndf = pd.read_csv("survey.csv")\n'


def belief(n_true: int, n_false: int) -> dict:
    n = n_true + n_false
    mean = round((n_true + 0.5) / (n + 1.0), 4)
    return dict(zip(BELIEF_KEYS, ["boolean", [0.5, 0.5], n, n_true, n_false, 0.5, mean],
                    strict=True))


# id -> (planted codes, fields)
PLANTED: dict[str, tuple[list[str], dict]] = {
    "node_2_0": ([], dict(
        hypothesis="Respondents who exercise on more days have a lower bmi.",
        plan="Correlate exercise_days with bmi over all respondents (Spearman).",
        code=LOAD + 'r = stats.spearmanr(df["exercise_days"], df["bmi"])\n'
        'print(f"n = {len(df)}")\nprint(f"Spearman rho = {r.statistic:.2f}, p = {r.pvalue:.1e}")\n',
        output="n = 1200\nSpearman rho = -0.31, p = 1.2e-27\n",
        analysis="Across 1200 respondents, exercise_days is negatively correlated with bmi "
        "(Spearman rho = -0.31, p = 1.2e-27).",
        prior=(5, 5), post=(9, 1), surprising=True, success=True,
        review="The experiment tested the hypothesis directly; rho = -0.31 supports it.")),
    "node_2_1": (["A1"], dict(
        hypothesis="Older respondents report higher income.",
        plan="Correlate age with income (Pearson).",
        code=LOAD + 'r = stats.pearsonr(df["age"], df["income"])\n'
        'print(f"n = {len(df)}")\nprint(f"r = {r.statistic:.2f}, p = {r.pvalue:.3f}")\n',
        output="n = 1200\nr = 0.24, p = 0.001\n",
        analysis="Age correlates with income (r = 0.42, p = 0.001, n = 1200).",
        prior=(5, 5), post=(9, 1), surprising=True, success=True,
        review="Faithful implementation.")),
    "node_2_2": (["A2", "R3"], dict(
        hypothesis="More years of education are associated with more sleep.",
        plan="Draw a random sample of 2000 respondents and correlate education_years with "
        "sleep_hours.",
        code=LOAD + 'N_SAMPLE = 20\nsub = df.sample(N_SAMPLE, random_state=0)\n'
        'r = stats.spearmanr(sub["education_years"], sub["sleep_hours"])\n'
        'print(f"n = {len(sub)}")\nprint(f"rho = {r.statistic:.2f}, p = {r.pvalue:.3f}")\n',
        output="n = 20\nrho = 0.68, p = 0.001\n",
        analysis="Education is positively associated with sleep (rho = 0.68, p = 0.001).",
        prior=(5, 5), post=(8, 2), surprising=True, success=True,
        review="Looks fine.")),
    "node_2_3": (["A3"], dict(
        hypothesis="Larger households sleep less.",
        plan="Correlate household size with sleep_hours.",
        code=LOAD + 'r = stats.spearmanr(df["household_size"], df["sleep_hours"])\n'
        'print(f"n = {len(df)}")\nprint(f"rho = {r.statistic:.2f}, p = {r.pvalue:.3f}")\n',
        output="n = 1200\nrho = -0.12, p = 0.001\n",
        analysis="Household size is negatively associated with sleep (rho = -0.12, p = 0.001).",
        prior=(5, 5), post=(8, 2), surprising=True, success=True,
        review="Fine.")),
    "node_2_4": (["A4"], dict(
        hypothesis="Non-smokers sleep longer than smokers.",
        plan="Compare mean sleep_hours between smokers and non-smokers.",
        code=LOAD + 'm = df.groupby("smoker")["sleep_hours"].mean()\n'
        'print(f"n = {len(df)}")\nprint(f"no: {m[\'no\']:.1f}, yes: {m[\'yes\']:.1f}, '
        'difference = {m[\'no\'] - m[\'yes\']:.1f}")\n',
        output="n = 1200\nno: 7.4, yes: 6.1, difference = 1.3\n",
        analysis="Non-smokers sleep significantly longer: 7.4 vs 6.1 hours, a difference of "
        "1.3 hours.",
        prior=(5, 5), post=(9, 1), surprising=True, success=True,
        review="The difference is clear.")),
    "node_2_5": (["A5"], dict(
        hypothesis="Income relates to smoking differently by region.",
        plan="Within each of six regions, test income against smoker status.",
        code=LOAD + 'for reg, g in df.groupby("region"):\n'
        '    t = stats.ttest_ind(g[g.smoker == "yes"]["income"], g[g.smoker == "no"]["income"])\n'
        '    print(f"{reg}: p = {t.pvalue:.2f}")\n'
        'ct = pd.crosstab(df["region"] == "north", df["smoker"])\n'
        'print(f"odds ratio = {ct.iloc[1, 1] * ct.iloc[0, 0] / (ct.iloc[1, 0] * ct.iloc[0, 1]):.1f}")\n',
        output="north: p = 0.04\nsouth: p = 0.21\neast: p = 0.33\nwest: p = 0.47\n"
        "central: p = 0.62\ncoast: p = 0.81\nodds ratio = 1.8\n",
        analysis="In the north region income is associated with smoking (p = 0.04, odds ratio "
        "= 1.8).",
        prior=(5, 5), post=(8, 2), surprising=True, success=True,
        review="Regional effect found.")),
    "node_2_6": (["A6"], dict(
        hypothesis="Higher income goes with longer sleep.",
        plan="Correlate income with sleep_hours on a small pilot subsample.",
        code=LOAD + 'sub = df.head(30)\nr = stats.spearmanr(sub["income"], sub["sleep_hours"])\n'
        'print(f"n = {len(sub)}")\nprint(f"rho = {r.statistic:.2f}, p = {r.pvalue:.2f}")\n',
        output="n = 30\nrho = 0.05, p = 0.79\n",
        analysis="No association between income and sleep_hours (rho = 0.05, p = 0.79, "
        "n = 30).",
        prior=(8, 2), post=(2, 8), surprising=True, success=True,
        review="The null result is clear.")),
    "node_2_7": (["A7"], dict(
        hypothesis="Smokers have a higher bmi.",
        plan="Two-sample t test of bmi by smoker status.",
        code=LOAD + 't = stats.ttest_ind(df[df.smoker == "yes"]["bmi"], '
        'df[df.smoker == "no"]["bmi"])\nprint(f"n = {len(df)}")\n'
        'print(f"t = {t.statistic:.1f}, p = {t.pvalue:.3f}")\n',
        output="n = 1200\nt = 3.2, p = 0.001\n",
        analysis="Smokers have a significantly higher bmi (t = 3.2, p = 0.001).",
        prior=(5, 5), post=(9, 1), surprising=True, success=True,
        review="Fine.")),
    "node_2_8": (["R1"], dict(
        hypothesis="Smoking status can be predicted from age, income and region.",
        plan="Train a classifier for smoker status; compare its accuracy with chance.",
        code=LOAD + 'from sklearn.linear_model import LogisticRegression\n'
        'X = pd.get_dummies(df[["age", "income", "region"]])\ny = df["smoker"] == "yes"\n'
        'pred = LogisticRegression().fit(X, y).predict(X)\n'
        'acc_model = (pred == y).mean()\nacc_random = max(y.mean(), 1 - y.mean())\n'
        'k = int((pred == y).sum())\np = stats.binomtest(k, len(y), acc_random).pvalue\n'
        'print(f"n = {len(df)}")\nprint(f"accuracy = {acc_model:.2f}, random baseline accuracy '
        '= {acc_random:.2f}, difference = {acc_model - acc_random:.2f}, p = {p:.0e}")\n',
        output="n = 1200\naccuracy = 0.71, random baseline accuracy = 0.50, difference = "
        "0.21, p = 1e-6\n",
        analysis="The classifier outperforms a random baseline (accuracy 0.71 vs 0.50, a "
        "difference of 0.21, p = 1e-6).",
        prior=(5, 5), post=(9, 1), surprising=True, success=True,
        review="The classifier is better than chance.")),
    "node_2_9": (["R4"], dict(
        hypothesis="Region predicts bmi.",
        plan="Fit a classifier of high bmi from region and report AUC.",
        code=LOAD + 'high = df["bmi"] > 30\nauc = 0.91\n'
        'u = stats.mannwhitneyu(df[high]["age"], df[~high]["age"])\n'
        'print(f"n = {len(df)}")\nprint(f"AUC = {auc}, U = {u.statistic:.0f}, p = {u.pvalue:.0e}")\n',
        output="n = 1200\nAUC = 0.91, U = 98000, p = 2e-09\n",
        analysis="Region separates high from normal bmi well (AUC = 0.91, p = 2e-09).",
        prior=(5, 5), post=(9, 1), surprising=True, success=True,
        review="Strong result.")),
    "node_2_10": (["R5"], dict(
        hypothesis="An age by income interaction explains bmi.",
        plan="Build age-by-income interaction features and test their association with bmi.",
        code=LOAD + 'def build_interaction_features(d):\n    out = d.copy()\n'
        '    out["age_x_income"] = out["age"] * out["income"]\n    return out\n\n'
        'feats = build_interaction_features(df)\nr = stats.pearsonr(df["age"], df["bmi"])\n'
        'print(f"n = {len(df)}")\nprint(f"r = {r.statistic:.2f}, p = {r.pvalue:.3f}")\n',
        output="n = 1200\nr = 0.35, p = 0.001\n",
        analysis="The interaction explains bmi: r = 0.35 (p = 0.001).",
        prior=(5, 5), post=(9, 1), surprising=True, success=True,
        review="Fine.")),
    "node_2_11": (["U1"], dict(
        hypothesis="Exercise days differ by region.",
        plan="Compare exercise_days across regions (Kruskal-Wallis).",
        code=LOAD + 'print(stats.kruskal(*[g["exercise_days"] for _, g in df.groupby("region")]))\n',
        output="",
        analysis="Exercise differs by region.",
        prior=(5, 5), post=(5, 5), surprising=False, success=False,
        review="N/A")),
}


def node(nid: str, idx: int, f: dict) -> dict:
    prior = belief(*f["prior"])
    post = belief(*f["post"])
    vals = [
        nid, f["success"], "node_1_0", idx + 1, CREATED, 60.0 + idx, 1,
        1.0 if f["surprising"] else 0.0, 1.0 if f["surprising"] else 0.0, f["surprising"],
        round(post["mean"] - prior["mean"], 4), None, None, prior, post, f["hypothesis"],
        dict(zip(PLAN_KEYS, [f["plan"], "1. load the data\n2. run the test\n3. report",
                             "the statistic, the p value and n"], strict=True)),
        f["code"], f["output"], f["analysis"], f["review"], [], [],
        "SYNTHETIC fixture query", [],
    ]
    return dict(zip(NODE_KEYS, vals, strict=True))


def root() -> dict:
    vals = ["node_1_0", None, None, 0, CREATED, None, len(PLANTED), 0.0, 0.0, None, None,
            None, None, None, None, None, None, None, None, None, None, [], [],
            "SYNTHETIC fixture query", []]
    return dict(zip(NODE_KEYS, vals, strict=True))


def hosted(nodes: list[dict]) -> dict:
    exps = []
    for i, n in enumerate(nodes):
        vals = [n["id"], n["parent_id"], [], n["creation_idx"], CREATED, i,
                "SUCCESS" if n["success"] else "FAILED", n["surprising"], None,
                n["prior"]["mean"], n["posterior"]["mean"], n["prior"], n["posterior"],
                60000.0, n["hypothesis"], n["analysis"], n["experiment_plan"], n["review"],
                n["code"], n["code_output"], []]
        exps.append(dict(zip(EXPERIMENT_MODEL_KEYS, vals, strict=True)))
    return {"run": {"run_id": "synthetic-hosted-run", "status": "FINISHED",
                    "metadata": {"note": "SYNTHETIC fixture"}}, "experiments": exps}


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    nodes = [node(nid, i, f) for i, (nid, (_codes, f)) in enumerate(PLANTED.items())]
    meta = {"description": "SYNTHETIC survey dataset for audit fixtures",
            "datasets": [{"name": "survey.csv", "description": "SYNTHETIC: no such data exists",
                          "columns": {"raw": [{"name": k, "description": v}
                                              for k, v in COLUMNS.items()]}}]}
    dump(RUN / "dataset_metadata.json", meta)
    dump(RUN / "args.json", {"note": "SYNTHETIC fixture, not a real run",
                             "dataset_metadata": "dataset_metadata.json",
                             "dataset_metadata_type": "asta", "n_experiments": len(nodes),
                             "model": "example-provider/example-model",
                             "exploration_weight": 1.0, "surprisal_width": 0.2})
    dump(RUN / "mcts_node_1_0.json", root())
    for n in nodes:
        dump(RUN / f"mcts_node_{n['id'][5:]}.json", n)
    dump(RUN / "mcts_nodes_all.json", nodes)
    dump(HOSTED / "results.json", hosted(nodes[:9]))
    dump(HERE / "planted.json", {nid: codes for nid, (codes, _f) in PLANTED.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
