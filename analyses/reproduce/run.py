"""Run both C3 analyses and write ``results/reproduce.json``.

    python analyses/reproduce/run.py            # needs: consilience-ai2 fetch codescientist
                                                #        codescientist-full50 discoverybench

(a) ``codescientist_reruns.py`` (descriptive) and (b) ``discoverybench_planted.py``
(synthetic); see each file for the design. Deterministic: fixed seeds, sorted inputs,
fallback F1 backend, no timestamps. Counts are reported with the n they are out of;
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
DB_SOURCE = "fetch:discoverybench"
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


def codescientist_metrics() -> list[dict]:
    s = cs.summarise(cs.analyse())
    kw = {"source": CS_SOURCE, "dev_or_heldout": "descriptive"}
    cav = ["reruns of the same idea in the same environment, not independent data in the "
           "asta-flows sense", "thresholds fixed by this analysis, not by the runs' authors",
           "only the full-50 batch with expert notes has released run outputs",
           "P1 not checked (records built in memory)"]
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


def discoverybench_metrics() -> list[dict]:
    s = db.summarise(db.analyse())
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


def main() -> int:
    metrics = codescientist_metrics() + discoverybench_metrics()
    path = write_results("reproduce", metrics, REPO / "results")
    print(f"wrote {path.relative_to(REPO)} ({len(metrics)} metrics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
