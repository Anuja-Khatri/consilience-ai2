"""HELD-OUT, preregistered: rules v0.2 on the 13 full50 runs no earlier analysis used (H3).

Implements prereg/audit/heldout_v2_prereg.md exactly (committed in 75b85b4, before this
script existed). Rules frozen at fd0187a (tree 5aa8b9c of consilience_ai2/audit): the
script checks that tree and relabels every metric exploratory if the rules changed.

H3: runs flagged at error severity by the v0.2 audit are less often rated ``faithful``
(``faithfullness_category`` in the with-expert-notes bulk TSV) than runs it passes.
Two-sided permutation test of T = share faithful (passed) - share faithful (flagged),
10,000 draws, ``numpy.random.default_rng(20261118)``. The v0.1 held-out result (H1, H2)
is separate and unchanged (``codescientist_heldout.py``).
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from codescientist_common import (
    audit_dir,
    error_flagged,
    example_dirs,
    faithfulness,
    flagged_codes,
    full50_dirs,
    full50_prefix,
    full50_zip,
    idea_of_dir,
    judgements,
    run_key_of_dir,
)
from rules_versions import V01, run_under, working_tree
from scipy.stats import fisher_exact

from consilience_ai2.core.results import metric

PREREG = ("prereg/audit/heldout_v2_prereg.md "
          "(commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828)")
FROZEN_COMMIT = "fd0187a8c38d7682e78f980f5b760a43a818c305"
FROZEN_TREE = "5aa8b9ccb6f4eda312cefb9a9ec1ad74ea657458"
SEED = 20261118
N_PERM = 10_000
ALPHA = 0.05
MIN_GROUP = 3
SRC = ("fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV "
       "faithfullness_category)")
TEST = (f"two-sided permutation, labels permuted across runs, {N_PERM} draws, numpy "
        f"default_rng({SEED}); T = share faithful (passed) - share faithful (flagged)")


def h1_units() -> list[str]:
    """The full50 directories that were units of the v0.1 H1 test."""
    judg = judgements()
    dev = set(example_dirs())
    out = []
    for d in full50_dirs():
        runs = judg.get(idea_of_dir(d), {})
        if run_key_of_dir(d) in runs and d not in dev and len(runs) >= 2:
            out.append(d)
    return out


def heldout_units() -> list[str]:
    """Full50 directories that are neither development-set directories nor H1 units."""
    dev = set(example_dirs())
    used = set(h1_units())
    return [d for d in full50_dirs() if d not in dev and d not in used]


def perm_test(y: np.ndarray, flag: np.ndarray, seed: int) -> tuple[float, float]:
    def t(f):
        return float(y[~f].mean() - y[f].mean())

    rng = np.random.default_rng(seed)
    t_obs = t(flag)
    perms = np.empty(N_PERM)
    for b in range(N_PERM):
        perms[b] = t(flag[rng.permutation(len(flag))])
    p = float((1 + np.sum(np.abs(perms) >= abs(t_obs) - 1e-12)) / (1 + N_PERM))
    return t_obs, p


def v01_flags() -> tuple[list[dict], dict]:
    """For ``run_under(V01, ...)``: the v0.1 error flag of every held-out run."""
    z, pre = full50_zip(), full50_prefix()
    return [], {"flags": {d: error_flagged(audit_dir(z, pre, d)) for d in heldout_units()}}


def _test_metrics(tag: str, y: np.ndarray, f: np.ndarray, split: str, cav: list[str],
                  what: str) -> tuple[list[dict], dict]:
    pre = f"audit.heldout_v2.{tag}"
    n = len(y)
    ms = [metric(f"{pre}.n_runs", n, n=n, source=SRC, dev_or_heldout=split, caveats=cav,
                 prereg=PREREG, unit="runs", description=what),
          metric(f"{pre}.n_flagged", int(f.sum()), n=n, source=SRC, dev_or_heldout=split,
                 caveats=cav, prereg=PREREG, unit="runs",
                 description="runs with an error-severity check")]
    info: dict = {"n": n, "n_flagged": int(f.sum()), "n_passed": int((~f).sum())}
    if f.sum() < MIN_GROUP or (~f).sum() < MIN_GROUP:
        info["result"] = "not testable"
        ms.append(metric(f"{pre}.perm_p", None, n=n, source=SRC, dev_or_heldout=split,
                         prereg=PREREG, caveats=cav + [
                             f"not testable: a group has fewer than {MIN_GROUP} runs "
                             f"({int((~f).sum())} passed, {int(f.sum())} flagged)"]))
        return ms, info
    t_obs, p = perm_test(y, f, SEED)
    table = [[int(y[~f].sum()), int((~f).sum() - y[~f].sum())],
             [int(y[f].sum()), int(f.sum() - y[f].sum())]]
    fisher_p = float(fisher_exact(table, alternative="two-sided").pvalue)
    info.update({"T": t_obs, "p": p, "share_passed": float(y[~f].mean()),
                 "share_flagged": float(y[f].mean()), "table_passed_flagged": table,
                 "fisher_p": fisher_p})
    ms += [
        metric(f"{pre}.share_faithful_passed", round(float(y[~f].mean()), 4),
               n=int((~f).sum()), source=SRC, dev_or_heldout=split, caveats=cav,
               prereg=PREREG, description="share rated faithful among passed runs"),
        metric(f"{pre}.share_faithful_flagged", round(float(y[f].mean()), 4),
               n=int(f.sum()), source=SRC, dev_or_heldout=split, caveats=cav,
               prereg=PREREG, description="share rated faithful among flagged runs"),
        metric(f"{pre}.t_difference", round(t_obs, 4), n=n, source=SRC,
               dev_or_heldout=split, caveats=cav, prereg=PREREG, test=TEST,
               description="share faithful, passed minus flagged (H3 predicts > 0)"),
        metric(f"{pre}.perm_p", round(p, 4), n=n, source=SRC, dev_or_heldout=split,
               caveats=cav, prereg=PREREG, test=TEST),
        metric(f"{pre}.fisher_p", round(fisher_p, 4), n=n, source=SRC,
               dev_or_heldout="exploratory", caveats=cav + ["secondary (a), no decision"],
               prereg=PREREG, test="two-sided Fisher exact test of the 2 x 2 table"),
    ]
    return ms, info


def run() -> tuple[list[dict], dict]:
    tree = working_tree()
    frozen = tree == FROZEN_TREE
    split = "heldout" if frozen else "exploratory"
    faith = faithfulness()
    z, pre = full50_zip(), full50_prefix()
    dev_ideas = {idea_of_dir(d) for d in example_dirs()}
    base_cav = ["outcome: faithfullness_category in the with-expert-notes bulk TSV, faithful = "
                "1, deviations or errors = 0 (model-generated in the released data)",
                "predictor: any error-severity check under rules v0.2 (audit-rules-2); R2 not "
                "evaluated"]
    if not frozen:
        base_cav.append("the audit rules changed after preregistration")

    def units_of(dirs: list[str]) -> tuple[list[dict], Counter]:
        units, excluded = [], Counter()
        for d in dirs:
            cat = faith.get(run_key_of_dir(d), "")
            if cat not in ("faithful", "deviations", "errors"):
                excluded["no faithfullness_category"] += 1
                continue
            node = audit_dir(z, pre, d)
            units.append({"dir": d, "idea": idea_of_dir(d), "category": cat,
                          "faithful": int(cat == "faithful"), "flagged": error_flagged(node),
                          "verdict_level": node.get("verdict_level"),
                          "codes": flagged_codes(node),
                          "error_codes": flagged_codes(node, ("error",)),
                          "dev_idea": idea_of_dir(d) in dev_ideas})
        return units, excluded

    def arrays(units):
        return (np.array([u["faithful"] for u in units], dtype=float),
                np.array([u["flagged"] for u in units], dtype=bool))

    # primary: H3 on the 13 unused runs
    units, excluded = units_of(heldout_units())
    y, f = arrays(units)
    cav = base_cav + ["13 full50 runs never used by the development set, H1 or H2"] + \
        [f"excluded, {k}: {v}" for k, v in sorted(excluded.items())]
    ms, info = _test_metrics("h3", y, f, split, cav, "held-out runs (units)")
    supported = bool(info.get("p") is not None and info["p"] < ALPHA and info["T"] > 0)
    info["supported"] = supported
    info["units"] = units
    info["excluded"] = dict(sorted(excluded.items()))
    if "p" in info:
        ms.append(metric("audit.heldout_v2.h3.supported", int(supported), n=len(units),
                         source=SRC, dev_or_heldout=split, prereg=PREREG, unit="1 = yes, 0 = no",
                         caveats=cav + [f"H3 {'supported' if supported else 'not supported'} "
                                        f"at alpha {ALPHA} (requires p < {ALPHA} and T > 0)"]))
    out_info: dict = {"rules_tree": tree, "frozen_tree": FROZEN_TREE, "frozen": frozen,
                      "frozen_commit": FROZEN_COMMIT, "h3": info}

    # (b) without runs of ideas in the example-experiments archive
    keep = [u for u in units if not u["dev_idea"]]
    yb, fb = arrays(keep)
    mb, ib = _test_metrics("h3.no_dev_ideas", yb, fb, "exploratory",
                           cav + ["secondary (b): runs of ideas in the example-experiments "
                                  "archive removed"], "held-out runs without dev ideas")
    ms += mb
    out_info["no_dev_ideas"] = ib

    # (c) the H1 units, v0.2 predictor, same outcome
    h1u, h1x = units_of(h1_units())
    yc, fc = arrays(h1u)
    mc, ic = _test_metrics("h1_units", yc, fc, "exploratory",
                           base_cav + ["secondary (c): the v0.1 H1 units, already used in the "
                                       "v0.1 held-out test, so not blind for the runs"] +
                           [f"excluded, {k}: {v}" for k, v in sorted(h1x.items())],
                           "v0.1 H1 units with a faithfulness category")
    ms += mc
    ic["excluded"] = dict(sorted(h1x.items()))
    ic["units"] = h1u
    out_info["h1_units"] = ic

    # (d) the v0.1 predictor on the same 13 runs (frozen v0.1 rules)
    _, v1 = run_under(V01, "codescientist_heldout_v2", "v01_flags")
    fd = np.array([v1["flags"][u["dir"]] for u in units], dtype=bool)
    md, idd = _test_metrics("h3.v01_predictor", y, fd, "exploratory",
                            cav + ["secondary (d): predictor = any error-severity check under "
                                   "the frozen v0.1 rules (audit-rules-1)"],
                            "held-out runs, v0.1 predictor")
    ms += md
    idd["flags"] = v1["flags"]
    out_info["v01_predictor"] = idd

    # (e) per code, descriptive
    per_code = Counter(c for u in units for c in u["codes"])
    out_info["per_code"] = dict(sorted(per_code.items()))
    for code, k in sorted(per_code.items()):
        ms.append(metric(f"audit.heldout_v2.h3.code.{code.lower()}", k, n=len(units),
                         source=SRC, dev_or_heldout="descriptive",
                         caveats=cav + ["secondary (e): held-out runs with this code at error "
                                        "or warning severity"], prereg=PREREG, unit="runs"))
    return ms, out_info
