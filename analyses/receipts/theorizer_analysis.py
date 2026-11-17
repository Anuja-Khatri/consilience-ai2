"""Evidence receipts on the released Theorizer theories (fetch: theorizer-paper-data).

Reads the four condition directories of the released HTML export through
``fetch.require`` (no network) and runs T1, T2, W1 and W2 on every law
(``consilience_ai2.receipts.theorizer``). Returns metric records, examples with
receipts and the per-condition summary used by ``run.py``.

Exploratory (labelled so): do theories with a high released predictive-accuracy support
fraction differ in T1 or W1 from theories with a low one? For each literature-supported
theory, the support fraction is the papers counted as supporting divided by the papers
counted as supporting or contradicting, summed over every prediction of every law that
has a predictive-accuracy page (theories with no such paper are excluded). Within each
literature-supported condition separately (the two conditions differ by design), theories
are split at that condition's median fraction: high is at or above the median. (Most
accuracy-focused theories have a fraction of exactly 1, so a strict "above the median"
split would leave the high group empty.) The outcome is binary per theory (any T1; any W1
at law or item level); the statistic is the difference in proportions (high minus low),
with a two-sided permutation test (10,000 relabellings, seed 0).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from consilience_ai2.core.results import metric
from consilience_ai2.fetch import require
from consilience_ai2.receipts import theorizer as th

SOURCE = "fetch:theorizer-paper-data"
LITERATURE = ("html_output-literature-supported-accuracy-focused",
              "html_output-literature-supported-novelty-focused")
PARAMETRIC = ("html_output-parametric-accuracy-focused",
              "html_output-parametric-novelty-focused")
SHORT = {LITERATURE[0]: "lit_accuracy", LITERATURE[1]: "lit_novelty",
         PARAMETRIC[0]: "param_accuracy", PARAMETRIC[1]: "param_novelty"}
PERMUTATIONS = 10_000
SEED = 0
EXCERPT = 120


def data_root() -> Path:
    z = require("theorizer-paper-data")
    root = z.with_suffix("")
    if not root.is_dir():
        raise SystemExit(f"{root} is missing: run consilience-ai2 fetch theorizer-paper-data --extract")
    return root


def wilson(k: int, n: int) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    from scipy.stats import binomtest
    ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    return round(float(ci.low), 6), round(float(ci.high), 6)


def rate(mid: str, k: int, n: int, caveats: list[str], **kw: Any) -> dict[str, Any]:
    lo, hi = wilson(k, n)
    return metric(mid, round(k / n, 6) if n else None, n=n, ci_lo=lo, ci_hi=hi,
                  source=SOURCE, dev_or_heldout=kw.pop("split", "descriptive"),
                  caveats=caveats if n else caveats + ["no cases"], unit="proportion", **kw)


def count(mid: str, v: int, desc: str, caveats: list[str] | None = None) -> dict[str, Any]:
    return metric(mid, v, n=None, source=SOURCE, dev_or_heldout="descriptive",
                  caveats=caveats or [], unit="count", description=desc)


def excerpt(s: str) -> str:
    s = " ".join(s.split())
    return s if len(s) <= EXCERPT else s[:EXCERPT - 3].rstrip() + "..."


def permutation_diff(x_high: np.ndarray, x_low: np.ndarray) -> tuple[float, float]:
    """Observed difference in means (high - low) and its two-sided permutation p."""
    obs = float(x_high.mean() - x_low.mean())
    pooled = np.concatenate([x_high, x_low])
    nh = len(x_high)
    rng = np.random.default_rng(SEED)
    hits = 0
    for _ in range(PERMUTATIONS):
        perm = rng.permutation(pooled)
        d = perm[:nh].mean() - perm[nh:].mean()
        if abs(d) >= abs(obs) - 1e-12:
            hits += 1
    return obs, (hits + 1) / (PERMUTATIONS + 1)


def run(is_model_id) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = data_root()
    metrics: list[dict[str, Any]] = []
    examples: dict[str, list[dict[str, Any]]] = {"T1": [], "T2": [], "W1": [], "W2": []}
    per: dict[str, dict[str, int]] = {}
    theory_rows: list[dict[str, Any]] = []
    totals = {"theories": 0, "laws": 0, "laws_parsed_statement": 0, "theories_with_laws": 0,
              "results_files": 0, "records": 0, "files_without_records": 0}
    for cond in LITERATURE + PARAMETRIC:
        cdir = root / cond
        recs, info = th.load_records(cdir)
        cache = th.RecordCache()
        totals["results_files"] += info["results_files"]
        totals["records"] += info["records"]
        totals["files_without_records"] += info["files_without_records"]
        c = dict(theories=0, laws=0, refs=0, unresolved=0, links=0, malformed=0,
                 t1_theories=0, t2=0, t2_scope=0, t2_evidence=0, law_checked=0, law_w1=0,
                 law_w2=0, items=0, items_checked=0, item_w1=0, item_w2=0,
                 items_without_ids=0, href_fallback=0, t1_links=0)
        pa_cache: dict[str, th.PredictiveAccuracy] = {}
        for t in th.iter_theories(cdir):
            findings, results = th.check_theory(t, recs, cond, cache=cache)
            c["theories"] += 1
            totals["theories"] += 1
            totals["theories_with_laws"] += bool(t.laws)
            any_t1 = any(f.code == "T1" for f in findings)
            any_w1 = any(f.code == "W1" for f in findings)
            c["t1_theories"] += any_t1
            for f in findings:
                if f.code == "T1":
                    c["t1_links"] += 1
                    c["malformed"] += not f.details["well_formed"]
                    href = f.details["href"]
                    c["href_fallback"] += bool(re.search(r"/e\d+\.\d+\.html#", href))
            for law, r in zip(t.laws, results, strict=True):
                c["laws"] += 1
                totals["laws"] += 1
                totals["laws_parsed_statement"] += law.statement is not None
                c["refs"] += r.ids
                c["unresolved"] += len(r.unresolved)
                c["links"] += sum(len(it.ids) for it in law.items)
                c["t2"] += r.empty_scope or r.empty_evidence
                c["t2_scope"] += r.empty_scope
                c["t2_evidence"] += r.empty_evidence
                if r.w1 is not None:
                    c["law_checked"] += 1
                    c["law_w1"] += bool(r.w1)
                    c["law_w2"] += bool(r.w2)
                c["items"] += len(law.items)
                c["items_checked"] += r.items_checked
                c["item_w1"] += r.w1_items
                c["item_w2"] += r.w2_items
                c["items_without_ids"] += r.items_without_ids
            if cond in LITERATURE:
                sup = con = 0
                n_pe = 0
                for law in t.laws:
                    if law.pe_file:
                        if law.pe_file not in pa_cache:
                            p = cdir / law.pe_file
                            pa_cache[law.pe_file] = th.parse_predictive_accuracy(
                                p.read_text(encoding="utf-8"), law.pe_file) if p.is_file() else None
                        pa = pa_cache[law.pe_file]
                        if pa is not None and pa.theory_id == t.id:
                            sup += pa.support
                            con += pa.contradict
                            n_pe += 1
                theory_rows.append({"condition": cond, "theory": t.id, "t1": any_t1,
                                    "w1": any_w1, "support": sup, "contradict": con,
                                    "pe_laws": n_pe})
            for f in findings:
                ex = examples.get(f.code)
                if ex is None or len(ex) >= 5:
                    continue
                if f.code in ("W1", "W2"):
                    law = t.laws[int(f.key.split("#statement-")[1].split("/")[0])]
                    if "/item-" in f.key:
                        claim = law.items[int(f.key.split("/item-")[1]) - 1].text
                    else:
                        claim = law.statement or ""
                    if is_model_id(claim):
                        continue
                    detail = ({"unsupported": f.details["unsupported"]} if f.code == "W1" else
                              {"claim_assertive": f.details["claim_assertive"],
                               "source_hedged": f.details["source_hedged"][:5]})
                    ex.append({"condition": cond, "file": t.file, "key": f.key,
                               "level": f.details["level"], "claim_excerpt": excerpt(claim),
                               "cited_ids": f.details["ids"][:6], **detail,
                               "receipt": f.receipt.to_dict()})
                elif f.code == "T1":
                    ex.append({"condition": cond, "file": t.file, "key": f.key,
                               **f.details, "receipt": f.receipt.to_dict()})
                else:
                    ex.append({"condition": cond, "file": t.file, "key": f.key, **f.details,
                               "receipt": f.receipt.to_dict()})
        per[cond] = c

    lit = {k: sum(per[cnd][k] for cnd in LITERATURE) for k in per[LITERATURE[0]]}
    allc = {k: sum(per[cnd][k] for cnd in per) for k in per[LITERATURE[0]]}
    cav_html = ["computed on the released HTML export, not the underlying theory store"]
    metrics += [
        count("receipts.theorizer.n_theories", totals["theories"],
              "theory files across the four released conditions"),
        count("receipts.theorizer.n_theories_literature", lit["theories"],
              "theories in the two literature-supported conditions"),
        count("receipts.theorizer.n_laws", totals["laws"], "laws (statements) parsed"),
        count("receipts.theorizer.n_laws_literature", lit["laws"],
              "laws in the literature-supported conditions"),
        count("receipts.theorizer.n_evidence_refs", lit["refs"],
              "distinct evidence IDs cited per law (law, ID pairs), literature conditions"),
        count("receipts.theorizer.n_evidence_links", lit["links"],
              "evidence links in law evidence lists, literature conditions"),
        count("receipts.theorizer.n_evidence_records", totals["records"],
              "evidence records (extraction instances) in the results files"),
        count("receipts.theorizer.n_extraction_files", totals["results_files"],
              "extraction result files (one extraction of one paper each)"),
        rate("receipts.theorizer.parse_coverage_theories", totals["theories_with_laws"],
             totals["theories"], cav_html, description="theory files with at least one law parsed"),
        rate("receipts.theorizer.parse_coverage_statements", totals["laws_parsed_statement"],
             totals["laws"], cav_html, description="laws whose statement text parsed"),
        rate("receipts.theorizer.parse_coverage_results_files",
             totals["results_files"] - totals["files_without_records"], totals["results_files"],
             cav_html + ["a results file with no record may be an extraction that found nothing"],
             description="results files with at least one evidence record parsed"),
        rate("receipts.theorizer.t1_rate", lit["unresolved"], lit["refs"],
             cav_html + ["literature-supported conditions; each (law, ID) pair counted once"],
             description="T1: cited evidence IDs that resolve to no evidence record"),
        count("receipts.theorizer.t1_malformed_ids", lit["malformed"],
              "T1 links whose ID is not of the form e<n>.<k>"),
        rate("receipts.theorizer.t1_theory_rate", lit["t1_theories"], lit["theories"],
             cav_html, description="theories with at least one T1"),
        rate("receipts.theorizer.t1_href_fallback_share", lit["href_fallback"], lit["t1_links"],
             cav_html, description="T1 links whose href is the export's fallback "
                                   "../results/<id>.html, which names no extraction file"),
        rate("receipts.theorizer.t2_rate", allc["t2"], allc["laws"],
             cav_html + ["all four conditions"],
             description="T2: laws with an empty scope or an empty evidence list"),
        rate("receipts.theorizer.t2_rate_literature", lit["t2"], lit["laws"], cav_html,
             description="T2 in the literature-supported conditions"),
        rate("receipts.theorizer.t2_empty_scope_rate", allc["t2_scope"], allc["laws"], cav_html),
        rate("receipts.theorizer.t2_empty_evidence_rate", allc["t2_evidence"], allc["laws"],
             cav_html),
        rate("receipts.theorizer.w1_law_rate", lit["law_w1"], lit["law_checked"],
             cav_html + ["laws with at least one resolved evidence record",
                         "the novelty-focused condition asks for quantitative predictions, "
                         "whose thresholds are absent from the evidence by design"],
             description="W1: a number in the law statement absent from its cited records"),
        rate("receipts.theorizer.w2_law_rate", lit["law_w2"], lit["law_checked"], cav_html,
             description="W2: assertive law over hedged cited records"),
        rate("receipts.theorizer.w1_item_rate", lit["item_w1"], lit["items_checked"],
             cav_html + ["evidence items with at least one resolved record",
                         "a record holds the extraction, not the full paper"],
             description="W1: a number in an evidence item absent from the records it cites"),
        rate("receipts.theorizer.w2_item_rate", lit["item_w2"], lit["items_checked"], cav_html,
             description="W2: assertive evidence item over hedged records"),
    ]
    for cond in LITERATURE:
        s = SHORT[cond]
        c = per[cond]
        metrics += [
            rate(f"receipts.theorizer.{s}.t1_rate", c["unresolved"], c["refs"], cav_html),
            rate(f"receipts.theorizer.{s}.w1_law_rate", c["law_w1"], c["law_checked"], cav_html),
            rate(f"receipts.theorizer.{s}.w2_law_rate", c["law_w2"], c["law_checked"], cav_html),
            rate(f"receipts.theorizer.{s}.w1_item_rate", c["item_w1"], c["items_checked"],
                 cav_html),
            rate(f"receipts.theorizer.{s}.w2_item_rate", c["item_w2"], c["items_checked"],
                 cav_html),
        ]
    for cond in PARAMETRIC:
        s = SHORT[cond]
        c = per[cond]
        metrics.append(rate(f"receipts.theorizer.{s}.t2_rate", c["t2"], c["laws"],
                            cav_html + ["parametric conditions cite no evidence IDs by design"]))

    # exploratory: predictive-accuracy split, within each literature-supported condition
    expl_summary: dict[str, Any] = {}
    for cond in LITERATURE:
        sc = SHORT[cond]
        rows = [r for r in theory_rows
                if r["condition"] == cond and r["support"] + r["contradict"] > 0]
        frac = np.array([r["support"] / (r["support"] + r["contradict"]) for r in rows])
        med = float(np.median(frac))
        high = frac >= med
        expl_cav = ["exploratory: not preregistered; one of several possible splits",
                    "support fraction = supporting / (supporting + contradicting) paper "
                    "counts summed over the theory's predictive-accuracy pages",
                    f"split at the condition's median support fraction ({med:.4f}): "
                    "high is at or above it",
                    f"high group n={int(high.sum())}, low group n={int((~high).sum())}",
                    "theories with no supporting or contradicting paper are excluded"]
        expl_summary[cond] = {"theories_with_pa": len(rows), "median_support_fraction": med,
                              "high": int(high.sum()), "low": int((~high).sum())}
        for outcome in ("t1", "w1"):
            x = np.array([1.0 if r[outcome] else 0.0 for r in rows])
            obs, p = permutation_diff(x[high], x[~high])
            test = f"two-sided permutation test, {PERMUTATIONS} relabellings, seed {SEED}"
            metrics.append(metric(
                f"receipts.theorizer.exploratory.{sc}.{outcome}_diff_high_minus_low_pa",
                round(obs, 6), n=len(rows), source=SOURCE, dev_or_heldout="exploratory",
                caveats=expl_cav + [f"permutation p={p:.4f}"],
                unit="difference in proportions", test=test,
                description=f"share of theories with any {outcome.upper()}: high minus low "
                            "predictive-accuracy support fraction"))
            metrics.append(metric(
                f"receipts.theorizer.exploratory.{sc}.{outcome}_diff_permutation_p",
                round(p, 6), n=len(rows), source=SOURCE, dev_or_heldout="exploratory",
                caveats=expl_cav, unit="p-value", test=test))
            for grp, mask in (("high", high), ("low", ~high)):
                metrics.append(rate(
                    f"receipts.theorizer.exploratory.{sc}.{outcome}_rate_{grp}_pa",
                    int(x[mask].sum()), int(mask.sum()), expl_cav, split="exploratory"))
    summary = {"per_condition": per, "totals": totals,
               "exploratory": expl_summary}
    return metrics, {"examples": examples, "summary": summary}
