"""Evidence receipts on SciArena-Eval (fetch: sciarena-eval).

Descriptive part (``run_descriptive``): every inline citation in every response is
resolved against the response's listed citations and checked for W1 and W2 against the
passages its sentence cites; quoted spans of three or more words are checked verbatim
(``consilience_ai2.receipts.sciarena``). No vote is read here.

Held-out part (``run_heldout``): the preregistered test of
``prereg/receipts/sciarena_prereg.md`` (committed before this code): in paired votes,
does the response with the higher W1+W2 flag rate per citation lose more often? Two-sided
exact sign test, a 10,000-draw sign-flip permutation null (seed 0), and the decision rule
written in the preregistration. W1 alone and W2 alone are exploratory secondaries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from consilience_ai2.core.results import metric
from consilience_ai2.fetch import require
from consilience_ai2.receipts import sciarena as sa

SOURCE = "fetch:sciarena-eval"
EXCERPT = 120


def load() -> list[dict[str, Any]]:
    return json.loads(Path(require("sciarena-eval")).read_text(encoding="utf-8"))


def wilson(k: int, n: int) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    from scipy.stats import binomtest
    ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    return round(float(ci.low), 6), round(float(ci.high), 6)


def rate(mid: str, k: int, n: int, caveats: list[str], **kw: Any) -> dict[str, Any]:
    lo, hi = wilson(k, n)
    return metric(mid, round(k / n, 6) if n else None, n=n, ci_lo=lo, ci_hi=hi,
                  source=SOURCE, dev_or_heldout="descriptive",
                  caveats=caveats if n else caveats + ["no cases"], unit="proportion", **kw)


def excerpt(s: str) -> str:
    s = " ".join(s.split())
    return s if len(s) <= EXCERPT else s[:EXCERPT - 3].rstrip() + "..."


def check_all(data: list[dict[str, Any]]) -> list[tuple[sa.ResponseResult, sa.ResponseResult]]:
    cache = sa.PassageCache()
    return [sa.check_vote(i, v, cache) for i, v in enumerate(data)]


def run_descriptive(data: list[dict[str, Any]], checked, is_model_id) -> tuple[list[dict], dict]:
    n = res = w1 = w2 = flag = 0
    q = qf = 0
    listed = listed_used = 0
    responses_with_cites = 0
    examples: dict[str, list[dict[str, Any]]] = {"W1": [], "W2": [], "unresolved": [],
                                                 "quote_not_found": []}
    for (a, b), v in zip(checked, data, strict=True):
        for r, key in ((a, "citations_a"), (b, "citations_b")):
            cl = v.get(key) or []
            listed += len(cl)
            used = {c.passage_index for c in r.citations if c.resolved}
            listed_used += len(used)
            responses_with_cites += bool(r.citations)
            for c in r.citations:
                n += 1
                res += c.resolved
                w1 += bool(c.w1)
                w2 += bool(c.w2)
                flag += bool(c.w1 or c.w2)
                ex = None
                if c.w1:
                    ex = ("W1", {"unsupported": c.unsupported_numbers})
                elif c.w2:
                    ex = ("W2", {"claim_assertive": c.w2_details.get("claim_assertive", []),
                                 "source_hedged": c.w2_details.get("source_hedged", [])[:5]})
                elif not c.resolved:
                    ex = ("unresolved", {})
                if ex and len(examples[ex[0]]) < 5 and not is_model_id(c.claim):
                    resp = v.get("response" + r.side) or ""
                    examples[ex[0]].append({
                        "vote_index": c.vote_index, "side": r.side, "marker": c.marker,
                        "claim_excerpt": excerpt(c.claim), **ex[1],
                        "receipt": {"source": f"sciarena-eval:{v.get('id')}/response{r.side}",
                                    "sha256": _sha(resp), "offset": c.start, "end": c.end}})
            for x in r.quotes:
                q += 1
                qf += x.outcome == "FOUND"
                if x.outcome != "FOUND" and len(examples["quote_not_found"]) < 5 \
                        and not is_model_id(x.text):
                    resp = v.get("response" + r.side) or ""
                    examples["quote_not_found"].append({
                        "vote_index": x.vote_index, "side": r.side,
                        "quote_excerpt": excerpt(x.text),
                        "receipt": {"source": f"sciarena-eval:{v.get('id')}/response{r.side}",
                                    "sha256": _sha(resp), "offset": x.start, "end": x.end}})
    cav = ["inline citations are matched by their concise_authors string "
           "(<Name> et al. <year><letter>)",
           "each citation is checked against the passages of every citation in its sentence"]
    metrics = [
        metric("receipts.sciarena.n_votes", len(data), n=None, source=SOURCE,
               dev_or_heldout="descriptive", caveats=[], unit="count"),
        metric("receipts.sciarena.n_inline_citations", n, n=None, source=SOURCE,
               dev_or_heldout="descriptive", caveats=cav[:1], unit="count"),
        metric("receipts.sciarena.n_listed_citations", listed, n=None, source=SOURCE,
               dev_or_heldout="descriptive", caveats=[], unit="count"),
        metric("receipts.sciarena.n_responses_with_citations", responses_with_cites,
               n=2 * len(data), source=SOURCE, dev_or_heldout="descriptive", caveats=[],
               unit="count"),
        rate("receipts.sciarena.resolution_rate", res, n, cav[:1],
             description="inline citations that resolve to a listed citation with passage text"),
        rate("receipts.sciarena.listed_cited_rate", listed_used, listed, cav[:1],
             description="listed citations that are cited inline at least once"),
        rate("receipts.sciarena.w1_rate", w1, res, cav,
             description="W1 per resolved inline citation"),
        rate("receipts.sciarena.w2_rate", w2, res, cav,
             description="W2 per resolved inline citation"),
        rate("receipts.sciarena.w1_or_w2_rate", flag, res, cav,
             description="W1 or W2 per resolved inline citation"),
        metric("receipts.sciarena.n_quoted_spans", q, n=None, source=SOURCE,
               dev_or_heldout="descriptive",
               caveats=["spans of three or more words inside double quotes, in sentences "
                        "with at least one resolved citation"], unit="count"),
        rate("receipts.sciarena.quote_found_rate", qf, q,
             ["verbatim after normalisation in one of the sentence's cited passages"],
             description="quoted spans found verbatim in a cited passage"),
    ]
    return metrics, {"examples": examples}


def _sha(text: str) -> str:
    from consilience_ai2.core.hashing import sha256_text
    return sha256_text(text)


# --------------------------------------------------------------------------- heldout

PREREG = "prereg/receipts/sciarena_prereg.md"
PERMUTATIONS = 10_000
SEED = 0


def flags(r: sa.ResponseResult, which: str) -> int:
    if which == "w1":
        return sum(bool(c.w1) for c in r.citations)
    if which == "w2":
        return sum(bool(c.w2) for c in r.citations)
    return sum(bool(c.w1) + bool(c.w2) for c in r.citations)


def paired_outcomes(data, checked, which: str) -> tuple[list[int], dict[str, int]]:
    """Per included vote: 1 when the response with the higher flag rate lost, else 0
    (the inclusion rules of the preregistration)."""
    out: list[int] = []
    excl = {"tie_or_missing_vote": 0, "no_citations": 0, "equal_rates": 0}
    for (a, b), v in zip(checked, data, strict=True):
        vote = v.get("vote")
        if vote not in ("A", "B"):
            excl["tie_or_missing_vote"] += 1
            continue
        if not a.citations or not b.citations:
            excl["no_citations"] += 1
            continue
        ra = flags(a, which) / len(a.citations)
        rb = flags(b, which) / len(b.citations)
        if ra == rb:
            excl["equal_rates"] += 1
            continue
        higher = "A" if ra > rb else "B"
        out.append(1 if vote != higher else 0)
    return out, excl


def sign_and_permutation(outcomes: list[int]) -> dict[str, Any]:
    from scipy.stats import binomtest
    n = len(outcomes)
    k = int(sum(outcomes))
    bt = binomtest(k, n, 0.5, alternative="two-sided")
    ci = bt.proportion_ci(confidence_level=0.95, method="exact")
    rng = np.random.default_rng(SEED)
    obs = abs(k - n / 2)
    x = np.array(outcomes)
    hits = 0
    for _ in range(PERMUTATIONS):
        flip = rng.random(n) < 0.5
        kd = int(np.where(flip, 1 - x, x).sum())
        if abs(kd - n / 2) >= obs:
            hits += 1
    return {"k": k, "n": n, "prop": k / n, "p_sign": float(bt.pvalue),
            "p_perm": (hits + 1) / (PERMUTATIONS + 1),
            "ci": (float(ci.low), float(ci.high))}


def decision(t: dict[str, Any]) -> str:
    if t["p_sign"] < 0.05 and t["prop"] > 0.5:
        return "supported"
    if t["p_sign"] < 0.05 and t["prop"] < 0.5:
        return "opposite direction"
    return "null"


def run_heldout(data, checked, prereg_commit: str) -> tuple[list[dict], dict]:
    metrics: list[dict[str, Any]] = []
    out: dict[str, Any] = {}
    test = ("two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal "
            f"rates excluded; permutation null: {PERMUTATIONS} sign flips, seed {SEED}")
    prereg = f"{PREREG} @ {prereg_commit}"
    for which, split, mid in (("w1w2", "heldout", "receipts.sciarena.heldout.higher_flag_rate_loses"),
                              ("w1", "exploratory", "receipts.sciarena.exploratory.higher_w1_rate_loses"),
                              ("w2", "exploratory", "receipts.sciarena.exploratory.higher_w2_rate_loses")):
        oc, excl = paired_outcomes(data, checked, which)
        t = sign_and_permutation(oc)
        d = decision(t)
        out[which] = {**t, "excluded": excl, "decision": d}
        cav = [f"decision under the preregistered rule: {d}",
               f"sign-test p={t['p_sign']:.4g}; permutation p={t['p_perm']:.4g}",
               f"excluded: {excl['tie_or_missing_vote']} tie or missing votes, "
               f"{excl['no_citations']} with a response citing nothing, "
               f"{excl['equal_rates']} with equal flag rates"]
        if split == "exploratory":
            cav.insert(0, "exploratory secondary analysis named in the preregistration; "
                          "not decision-bearing")
        metrics.append(metric(mid, round(t["prop"], 6), n=t["n"], ci_lo=round(t["ci"][0], 6),
                              ci_hi=round(t["ci"][1], 6), source=SOURCE, dev_or_heldout=split,
                              caveats=cav, unit="proportion of included votes", test=test,
                              prereg=prereg,
                              description="share of included votes in which the response "
                                          "with the higher flag rate lost"))
        base = mid.replace("_loses", "")
        metrics.append(metric(f"{base}_sign_p", round(t["p_sign"], 6), n=t["n"], source=SOURCE,
                              dev_or_heldout=split, caveats=cav, unit="p-value", test=test,
                              prereg=prereg))
        metrics.append(metric(f"{base}_permutation_p", round(t["p_perm"], 6), n=t["n"],
                              source=SOURCE, dev_or_heldout=split, caveats=cav, unit="p-value",
                              test=test, prereg=prereg))
    return metrics, out
