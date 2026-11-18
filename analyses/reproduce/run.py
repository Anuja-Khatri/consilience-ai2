"""Run both C3 analyses and write ``results/reproduce.json``.

    python analyses/reproduce/run.py   # needs: consilience-ai2 fetch codescientist
                                       #   codescientist-full50 discoverybench
                                       #   codescientist-example-experiments

(a) ``codescientist_reruns.py`` (descriptive) and (b) ``discoverybench_planted.py``
(synthetic); see each file for the design. Both carry the v0.1 numbers and, beside them,
the v0.2 numbers (``*.v0_2.*``; rules in ``prereg/reproduce/cs_extraction_v0_2.md``).
Deterministic: fixed seeds, sorted inputs, fallback F1 backend, no timestamps. Counts are reported with the n they are out of;
rates carry a Wilson 95% interval.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import codescientist_reruns as cs  # noqa: E402
import discoverybench_planted as db  # noqa: E402

from consilience_ai2.core.results import metric, write_results  # noqa: E402

REPO = HERE.parent.parent
CS_SOURCE = "fetch:codescientist+codescientist-full50"
CS_SOURCE_V02 = "fetch:codescientist+codescientist-full50+codescientist-example-experiments"
DB_SOURCE = "fetch:discoverybench"
PREREG_V02 = "prereg/reproduce/cs_extraction_v0_2.md @ 0df1320"
DEVIATIONS_V02 = "prereg/reproduce/cs_extraction_v0_2_deviations.md"
V01_NOTE = ("v0.1 extraction rule (the single non-random bootstrap block of the final "
            "results.json); the v0.2 rule is reported beside it as the *.v0_2.* metrics")
Z95 = 1.959963984540054


def wilson(k: int, n: int) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    den = 1 + Z95 ** 2 / n
    c = (p + Z95 ** 2 / (2 * n)) / den
    h = Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) / den
    return round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_.\-]+", "-", s.lower()).strip("-")


def rate(mid: str, k: int, n: int, **kw) -> dict:
    lo, hi = wilson(k, n)
    return metric(mid, round(k / n, 4) if n else None, n=n, ci_lo=lo, ci_hi=hi, unit="fraction",
                  **kw)


def count(mid: str, k: int, n: int | None, **kw) -> dict:
    return metric(mid, k, n=n, unit="count", **kw)


CS_CAVEATS = ["reruns of the same idea in the same environment, not independent data in "
              "the asta-flows sense",
              "thresholds fixed by this analysis, not by the runs' authors",
              "only the full-50 batch with expert notes has released run outputs",
              "P1 not checked (records built in memory)"]


def codescientist_metrics(res: dict) -> list[dict]:
    s = cs.summarise(res)
    kw = {"source": CS_SOURCE, "dev_or_heldout": "descriptive"}
    cav = CS_CAVEATS + [V01_NOTE]
    n = s["n_pairs"]
    out = [
        count("reproduce.cs.pairs", n, n, caveats=cav, description="(source run, later run) "
              "pairs from ideas with at least 2 completed runs", **kw),
        count("reproduce.cs.ideas_2plus_runs", s["n_ideas_2plus"], s["n_ideas_meta"],
              caveats=cav, description="ideas with at least 2 completed runs, of the batch's "
              "ideas", **kw),
        rate("reproduce.cs.coverage_recoverable", s["coverage"].get("recoverable", 0), n,
             caveats=cav, description="pairs whose two runs both give a recoverable primary "
             "bootstrap comparison", **kw),
        rate("reproduce.cs.agreement_with_run_labels", s["agree"], s["n_labelled"],
             caveats=cav + ["their label is a language-model judgement of the run's write-up"],
             description="pairs where our V1 verdict matches CodeScientist's judgement of the "
             "reproduction run (reproduced~support, not_reproduced~refute, "
             "inconclusive~inconclusive)", test="exact agreement", **kw),
        count("reproduce.cs.p2_verbatim", s["p2"].get("verbatim", 0), n, caveats=cav,
              description="pairs whose two runs state the hypothesis in identical words", **kw),
    ]
    for reason, k in sorted(s["coverage"].items()):
        out.append(count(f"reproduce.cs.coverage.{slug(reason)}", k, n, caveats=cav, **kw))
    for cls, k in sorted(s["f1"].items()):
        out.append(count(f"reproduce.cs.f1.{slug(cls)}", k, s["n_recoverable"], caveats=cav,
                         description="F1 among recoverable pairs", **kw))
    for key, table in (("d1", s["d1"]), ("v1", s["v1"]), ("outcome", s["outcome"])):
        for cls, k in sorted(table.items()):
            out.append(count(f"reproduce.cs.{key}.{slug(cls)}", k, n, caveats=cav, **kw))
    for cell, k in sorted(s["cross"].items()):
        ours, theirs = cell.split("|")
        out.append(count(f"reproduce.cs.vs_labels.ours_{ours}.theirs_{theirs}", k,
                         s["n_labelled"], caveats=cav, **kw))
    for cell, k in sorted(s["consistency_cross"].items()):
        same, ours = cell.split("|")
        out.append(count(f"reproduce.cs.vs_consistency.their_judgements_{same}.ours_{ours}",
                         k, s["n_both_judged"], caveats=cav,
                         description="their judgements of the two runs of a pair (same or "
                         "different) beside our V1 verdict for the pair", **kw))
    return out


def codescientist_metrics_v02_prereg(res: dict) -> list[dict]:
    """The v0.2 rule exactly as preregistered (before the deviations), on the same pairs:
    coverage, verdicts and the per-comparison table, for comparison with the corrected
    rule."""
    s = cs.summarise_v02(res, "v02p")
    kw = {"source": CS_SOURCE, "dev_or_heldout": "descriptive", "prereg": PREREG_V02}
    cav = CS_CAVEATS + [f"the v0.2 rule as preregistered, superseded by the corrected rule "
                        f"(deviations in {DEVIATIONS_V02})"]
    P = "reproduce.cs.v0_2.as_preregistered"
    n = s["n_pairs"]
    out = [rate(f"{P}.coverage_recoverable", s["coverage"].get("recoverable", 0), n,
                caveats=cav, **kw)]
    for reason, k in sorted(s["coverage"].items()):
        out.append(count(f"{P}.coverage.{slug(reason)}", k, n, caveats=cav, **kw))
    for key in ("d1", "v1", "outcome"):
        for cls, k in sorted(s[key].items()):
            out.append(count(f"{P}.{key}.{slug(cls)}", k, n, caveats=cav, **kw))
    pc = s["per_comparison"]
    out.append(count(f"{P}.per_comparison.n", pc["n"], None, caveats=cav, **kw))
    for v in ("reproduced", "not_reproduced", "inconclusive"):
        out.append(count(f"{P}.per_comparison.v1.{v}", pc["verdict"].get(v, 0), pc["n"],
                         caveats=cav, **kw))
    return out


def codescientist_metrics_v02(res: dict) -> list[dict]:
    """The v0.2 extraction rule on the same 65 pairs (``prereg/reproduce/
    cs_extraction_v0_2.md`` with the corrections in ``..._deviations.md``), its change
    from v0.1, and the second-batch search."""
    s = cs.summarise_v02(res)
    kw = {"source": CS_SOURCE, "dev_or_heldout": "descriptive", "prereg": PREREG_V02}
    cav = CS_CAVEATS + ["v0.2 extraction rule: results.json, then to_save/, then log.json "
                        "of the final iteration; several candidates resolved by the "
                        "hypothesis, then the experiment plan, else left no_data",
                        f"corrected after one run of the preregistered rule and before "
                        f"any number was committed; see {DEVIATIONS_V02}"]
    P = "reproduce.cs.v0_2"
    n = s["n_pairs"]
    out = [
        rate(f"{P}.coverage_recoverable", s["coverage"].get("recoverable", 0), n, caveats=cav,
             description="pairs whose two runs both give a primary bootstrap comparison "
             "under the v0.2 rule", **kw),
        count(f"{P}.newly_recoverable", s["n_newly_recoverable"], n, caveats=cav,
              description="pairs recoverable under v0.2 and not under v0.1", **kw),
        rate(f"{P}.agreement_with_run_labels", s["agree"], s["n_labelled"],
             caveats=cav + ["their label is a language-model judgement of the run's "
                            "write-up"],
             description="pairs where our V1 verdict matches CodeScientist's judgement of "
             "the reproduction run", test="exact agreement", **kw),
        count(f"{P}.runs", s["runs"]["n_runs"], None, caveats=cav,
              description="completed runs of the ideas read", **kw),
        count(f"{P}.runs.files_repaired", s["runs"]["files_repaired"], s["runs"]["n_runs"],
              caveats=cav, description="output files that parsed only with the restricted "
              "literal reader", **kw),
    ]
    for reason, k in sorted(s["coverage"].items()):
        out.append(count(f"{P}.coverage.{slug(reason)}", k, n, caveats=cav, **kw))
    for st, k in sorted(s["runs"]["status"].items()):
        out.append(count(f"{P}.runs.status.{slug(st)}", k, s["runs"]["n_runs"], caveats=cav,
                         **kw))
    for tb, k in sorted(s["runs"]["tier_basis"].items()):
        tier, basis = tb.split("|")
        out.append(count(f"{P}.runs.ok_by.{slug(tier)}.{slug(basis)}", k,
                         s["runs"]["n_runs"], caveats=cav,
                         description="readable runs by tier and basis of the primary", **kw))
    for cls, k in sorted(s["f1"].items()):
        out.append(count(f"{P}.f1.{slug(cls)}", k, s["n_recoverable"], caveats=cav,
                         description="F1 among recoverable pairs", **kw))
    for key in ("d1", "v1", "outcome"):
        for cls, k in sorted(s[key].items()):
            out.append(count(f"{P}.{key}.{slug(cls)}", k, n, caveats=cav, **kw))
    for cell, k in sorted(s["cross"].items()):
        ours, theirs = cell.split("|")
        out.append(count(f"{P}.vs_labels.ours_{ours}.theirs_{theirs}", k, s["n_labelled"],
                         caveats=cav, **kw))
    for cell, k in sorted(s["verdict_transitions"].items()):
        a, b = cell.split("|")
        out.append(count(f"{P}.transition.{a}.to_{b}", k, n, caveats=cav,
                         description="v0.1 verdict to v0.2 verdict, per pair", **kw))
    pc = s["per_comparison"]
    pcav = cav + ["per comparison, not per pair: pairs whose primary stays ambiguous, each "
                  "comparison found in both runs judged on its own; not counted among the "
                  "65 pairs"]
    out.append(count(f"{P}.per_comparison.n", pc["n"], None, caveats=pcav, **kw))
    out.append(count(f"{P}.per_comparison.pairs", pc["n_pairs"], n, caveats=pcav,
                     description="pairs contributing at least one matched comparison", **kw))
    for v in ("reproduced", "not_reproduced", "inconclusive"):
        out.append(count(f"{P}.per_comparison.v1.{v}", pc["verdict"].get(v, 0), pc["n"],
                         caveats=pcav, **kw))
    for cls, k in sorted(pc["outcome"].items()):
        out.append(count(f"{P}.per_comparison.outcome.{slug(cls)}", k, pc["n"], caveats=pcav,
                         **kw))
    b2 = s["batch2"]
    bkw = {"source": CS_SOURCE_V02, "dev_or_heldout": "descriptive", "prereg": PREREG_V02}
    bcav = ["the full-50 batch without expert notes: bulk and meta-analysis tables are "
            "released, run outputs are not"]
    out += [
        count("reproduce.cs.batch2.completed_runs", b2["completed_runs"], None, caveats=bcav,
              description="completed reruns in the batch without expert notes", **bkw),
        count("reproduce.cs.batch2.pairs", b2["pairs"], None, caveats=bcav,
              description="(source, later run) pairs that batch would give", **bkw),
        count("reproduce.cs.batch2.run_directories_named", b2["run_directories_named"], None,
              caveats=bcav, description="run directories the batch's experiment list names",
              **bkw),
    ]
    for where, k in sorted(b2["run_directories_found"].items()):
        out.append(count(f"reproduce.cs.batch2.found_in.{slug(where)}", k,
                         b2["run_directories_named"], caveats=bcav,
                         description="of those run directories, present here", **bkw))
    return out


def discoverybench_metrics(s: dict) -> list[dict]:
    kw = {"source": DB_SOURCE, "dev_or_heldout": "synthetic"}
    cav = ["planted = in the gold expression; the expression may be non-linear, so a planted "
           "effect need not be a linear correlation",
           "null = named by no query of the task; indirect dependence through the generator "
           "is possible", "row halves of one synthetic table, seed 0"]
    c = s["counts"]
    out = [
        count("reproduce.db.queries_usable", c["queries_usable"], c["queries"], caveats=cav,
              description="queries with a target column and a gold expression", **kw),
        count("reproduce.db.tasks", c["tasks"], None, caveats=cav, **kw),
    ]
    for kind in ("planted", "null"):
        g = s[kind]
        n = g["n"]
        for v in ("reproduced", "not_reproduced", "inconclusive"):
            out.append(count(f"reproduce.db.{kind}.{v}", g["verdict"].get(v, 0), n,
                             caveats=cav, **kw))
        for cls, k in sorted(g["outcome"].items()):
            out.append(count(f"reproduce.db.{kind}.outcome.{slug(cls)}", k, n, caveats=cav, **kw))
        out.append(rate(f"reproduce.db.{kind}.reproduced_rate", g["verdict"].get("reproduced", 0),
                        n, caveats=cav, **kw))
        if kind == "null":
            ok = g["verdict"].get("not_reproduced", 0) + g["verdict"].get("inconclusive", 0)
            out.append(rate("reproduce.db.null.not_reproduced_or_inconclusive_rate", ok, n,
                            caveats=cav, **kw))
        dec = g["decidable_verdict"]
        nd = sum(dec.values())
        out.append(rate(f"reproduce.db.{kind}.decidable_reproduced_rate", dec.get("reproduced", 0),
                        nd, caveats=cav, description="among pairs D1 classes decidable", **kw))
        ss = g["source_significant_verdict"]
        ns = sum(ss.values())
        out.append(rate(f"reproduce.db.{kind}.source_significant_reproduced_rate",
                        ss.get("reproduced", 0), ns, caveats=cav,
                        description="among pairs whose source half has p < alpha", **kw))
        out.append(rate(f"reproduce.db.{kind}.small_underpowered_rate",
                        g["small_decidability"].get("underpowered", 0), g["n_small"], caveats=cav,
                        description=f"reproductions on {db.SMALL_N} rows classed underpowered",
                        **kw))
        emp = g["small_vs_empirical"]
        agree = emp.get("decidable|emp>=0.8", 0) + emp.get("underpowered|emp<0.8", 0)
        out.append(rate(f"reproduce.db.{kind}.small_d1_agrees_with_empirical_power", agree,
                        sum(emp.values()), caveats=cav,
                        description=f"D1 class at {db.SMALL_N} rows vs empirical power from "
                        f"{db.DRAWS} subsamples (>= 0.8 means decidable)",
                        test="exact agreement", **kw))
        out.append(count(f"reproduce.db.{kind}.full_data_significant",
                         g["full_data_significant"], n, caveats=cav,
                         description="pairs with p < 0.05 on all rows", **kw))
        out.append(count(f"reproduce.db.{kind}.reproduced_and_full_data_significant",
                         g["reproduced_full_data_significant"], g["verdict"].get("reproduced", 0),
                         caveats=cav, **kw))
    return out


def discoverybench_metrics_v02(s: dict) -> list[dict]:
    """Sensitivity (Spearman verdicts; Pearson, Spearman and MI detection on half B) and
    the derived planted pairs. Rules in ``prereg/reproduce/cs_extraction_v0_2.md``."""
    kw = {"source": DB_SOURCE, "dev_or_heldout": "synthetic", "prereg": PREREG_V02}
    cav = ["sensitivity analysis next to the Pearson verdicts, which it does not replace",
           "row halves of one synthetic table, seed 0"]
    dcav = ["derived: predictors read from column names in the prose gold hypothesis "
            "(exactly two named columns); not the generator's gold expression"]
    P = "reproduce.db.v0_2"
    c = s["counts"]
    q = c["queries"]
    out = [
        count(f"{P}.queries_gold_text_only", c.get("queries_gold_text_only", 0), q,
              caveats=dcav, description="queries with a prose gold hypothesis and no gold "
              "expression", **kw),
        count(f"{P}.queries_no_gold", c.get("queries_no_gold", 0), q, caveats=dcav,
              description="queries with neither", **kw),
    ]
    for k in ("0", "1", "2", "3+"):
        out.append(count(f"{P}.derived_named.{slug(k)}", c.get(f"derived_named_{k}", 0),
                         c.get("queries_gold_text_only", 0), caveats=dcav,
                         description=f"prose gold hypotheses naming {k} columns", **kw))
    for k in ("already_planted_or_repeated", "not_numeric", "constant_in_a_half"):
        out.append(count(f"{P}.derived_skipped.{slug(k)}", c.get(f"derived_skipped_{k}", 0),
                         c.get("derived_named_2", 0), caveats=dcav, **kw))
    for kind in ("planted", "null", "derived"):
        g = s[kind]
        gc = cav + (dcav if kind == "derived" else [])
        n = g["n"]
        if kind == "derived":
            for v in ("reproduced", "not_reproduced", "inconclusive"):
                out.append(count(f"{P}.derived.{v}", g["verdict"].get(v, 0), n, caveats=gc,
                                 description="Pearson verdict, derived pairs", **kw))
            for cls, k in sorted(g["outcome"].items()):
                out.append(count(f"{P}.derived.outcome.{slug(cls)}", k, n, caveats=gc, **kw))
            out.append(rate(f"{P}.derived.reproduced_rate", g["verdict"].get("reproduced", 0),
                            n, caveats=gc, **kw))
            dec = g["decidable_verdict"]
            out.append(rate(f"{P}.derived.decidable_reproduced_rate",
                            dec.get("reproduced", 0), sum(dec.values()), caveats=gc,
                            description="among pairs D1 classes decidable", **kw))
        sp = g["spearman"]
        for v in ("reproduced", "not_reproduced", "inconclusive"):
            out.append(count(f"{P}.{kind}.spearman.{v}", sp["verdict"].get(v, 0), sp["n"],
                             caveats=gc, **kw))
        for cls, k in sorted(sp["outcome"].items()):
            out.append(count(f"{P}.{kind}.spearman.outcome.{slug(cls)}", k, sp["n"],
                             caveats=gc, **kw))
        out.append(rate(f"{P}.{kind}.spearman.reproduced_rate",
                        sp["verdict"].get("reproduced", 0), sp["n"], caveats=gc, **kw))
        out.append(rate(f"{P}.{kind}.spearman.underpowered_rate",
                        sp["decidability"].get("underpowered", 0), sp["n"], caveats=gc,
                        description="Spearman records D1 classes underpowered", **kw))
        sdec = sp["decidable_verdict"]
        out.append(rate(f"{P}.{kind}.spearman.decidable_reproduced_rate",
                        sdec.get("reproduced", 0), sum(sdec.values()), caveats=gc,
                        description="among Spearman records D1 classes decidable", **kw))
        if kind == "null":
            ok = sp["verdict"].get("not_reproduced", 0) + sp["verdict"].get("inconclusive", 0)
            out.append(rate(f"{P}.null.spearman.not_reproduced_or_inconclusive_rate", ok,
                            sp["n"], caveats=gc, **kw))
        det = g["detected_b"]
        for m in ("pearson", "spearman", "mi"):
            out.append(rate(f"{P}.{kind}.detected_b.{m}", det[m], det["n"], caveats=gc,
                            description=f"pairs whose half-B {m} test has p < 0.05",
                            test={"pearson": "Pearson r, two-sided",
                                  "spearman": "Spearman rho, two-sided",
                                  "mi": f"binned mutual information, {db.MI_PERMUTATIONS} "
                                        "permutations"}[m], **kw))
        out.append(count(f"{P}.{kind}.detected_b.mi_not_pearson", det["mi_not_pearson"],
                         det["n"], caveats=gc, description="detected by MI, missed by "
                         "Pearson, on half B", **kw))
    return out


def main() -> int:
    cs_res = cs.analyse()
    db_sum = db.summarise(db.analyse())
    metrics = (codescientist_metrics(cs_res) + codescientist_metrics_v02(cs_res)
               + codescientist_metrics_v02_prereg(cs_res)
               + discoverybench_metrics(db_sum) + discoverybench_metrics_v02(db_sum))
    path = write_results("reproduce", metrics, REPO / "results")
    print(f"wrote {path.relative_to(REPO)} ({len(metrics)} metrics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
