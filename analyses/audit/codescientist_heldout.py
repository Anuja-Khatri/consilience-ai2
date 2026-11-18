"""HELD-OUT, preregistered: does the audit's flag predict CodeScientist rerun consistency
(H1, confirmatory) and external soundness ratings (H2, exploratory)?

Implements prereg/audit/heldout_prereg.md exactly (committed in 3d86441, before this
script existed). Rules frozen at d24d2f7: the script checks the git tree of
consilience_ai2/audit and relabels the results exploratory if the rules changed.

This is the rules v0.1 result and it stays one. Since rules v0.2, ``run_all.py`` runs this
module with the frozen v0.1 rules taken from git (``rules_versions.run_under(V01, ...)``),
so the tree it checks is the frozen tree itself and the published numbers are
recomputed, never re-scored with new rules. The v0.2 held-out test is a separate
preregistration (``codescientist_heldout_v2.py``).
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
from codescientist_common import (
    EXAMPLES_PREFIX,
    audit_dir,
    error_flagged,
    example_dirs,
    examples_zip,
    flagged_codes,
    full50_dirs,
    full50_prefix,
    full50_zip,
    idea_of_dir,
    judgements,
    reviews,
    run_key_of_dir,
    soundness_score,
)
from codescientist_dev import TABLE4
from rules_versions import working_tree
from scipy.stats import mannwhitneyu

from consilience_ai2.core.results import metric

PREREG = "prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026)"
FROZEN_COMMIT = "d24d2f7738496448b9c68fa529ce89cda7ce5c2d"
FROZEN_TREE = "cca16a044d8074fd2672026af812a67dd6cafc31"
SEED = 20261117
N_PERM = 10_000
ALPHA = 0.05
REPO = Path(__file__).resolve().parents[2]
SRC_H1 = "fetch:codescientist-full50 + fetch:codescientist (metaanalysis)"
SRC_H2 = "fetch:codescientist (reviews) + fetch:codescientist-example-experiments"


def rules_tree() -> str | None:
    """Git tree id of consilience_ai2/audit at HEAD, or None when git is unavailable or the
    directory has uncommitted changes (then the rules cannot be shown to be frozen). Under
    ``rules_versions.run_under`` it is the frozen tree the rules were built from."""
    return working_tree()


def _perm_p(t_obs: float, perm: np.ndarray) -> float:
    return float((1 + np.sum(np.abs(perm) >= abs(t_obs) - 1e-12)) / (1 + len(perm)))


def stratified_perm(y: np.ndarray, flag: np.ndarray, strata: list[str], rng) -> tuple[float, float]:
    """T = mean(y | passed) - mean(y | flagged); labels permuted within strata."""
    def t(f):
        return float(y[~f].mean() - y[f].mean())

    t_obs = t(flag)
    groups = defaultdict(list)
    for i, s in enumerate(strata):
        groups[s].append(i)
    idx = [np.array(v) for _, v in sorted(groups.items())]
    perms = np.empty(N_PERM)
    for b in range(N_PERM):
        f = flag.copy()
        for ix in idx:
            f[ix] = flag[ix][rng.permutation(len(ix))]
        perms[b] = t(f)
    return t_obs, _perm_p(t_obs, perms)


def plain_perm(y: np.ndarray, flag: np.ndarray, rng) -> tuple[float, float]:
    return stratified_perm(y, flag, ["all"] * len(y), rng)


def mwu(y: np.ndarray, flag: np.ndarray) -> tuple[float | None, float | None]:
    a, b = y[~flag], y[flag]
    if len(a) == 0 or len(b) == 0:
        return None, None
    r = mannwhitneyu(a, b, alternative="two-sided")
    rank_biserial = 2 * float(r.statistic) / (len(a) * len(b)) - 1  # passed vs flagged
    return float(r.pvalue), rank_biserial


def h1(frozen: bool) -> tuple[list[dict], dict]:
    judg = judgements()
    dev_dirs = set(example_dirs())
    dev_ideas = {idea for _, idea, _, _ in TABLE4}
    z, pre = full50_zip(), full50_prefix()
    units, excluded = [], defaultdict(int)
    for d in full50_dirs():
        idea = idea_of_dir(d)
        key = run_key_of_dir(d)
        runs = judg.get(idea, {})
        if key not in runs:
            excluded["no per-run judgement"] += 1
            continue
        if d in dev_dirs:
            excluded["development-set directory"] += 1
            continue
        if len(runs) < 2:
            excluded["idea has fewer than 2 judged runs"] += 1
            continue
        mine = runs[key]
        others = [v for k, v in runs.items() if k != key]
        loo = sum(1 for v in others if v == mine) / len(others)
        node = audit_dir(z, pre, d)  # no rerun labels: R2 not evaluated
        units.append({"dir": d, "idea": idea, "judgement": mine, "k": len(runs),
                      "loo_agreement": loo, "flagged": error_flagged(node),
                      "verdict": node["verdict"], "codes": flagged_codes(node),
                      "error_codes": flagged_codes(node, ("error",)),
                      "dev_idea": idea in dev_ideas})
    y = np.array([u["loo_agreement"] for u in units], dtype=float)
    f = np.array([u["flagged"] for u in units], dtype=bool)
    strata = [u["idea"] for u in units]
    split = "heldout" if frozen else "exploratory"
    cav = ["outcome: leave-one-out agreement of the meta-analysis per-run judgements (which "
           "are model-generated in the released data)",
           "predictor: any error-severity audit check; R2 not evaluated"]
    if not frozen:
        cav.append("the audit rules changed after preregistration")
    info: dict = {"units": units, "excluded": dict(sorted(excluded.items())),
                  "n_flagged": int(f.sum()), "n_passed": int((~f).sum())}
    ms = [metric("audit.heldout.h1.n_runs", len(units), n=len(units), source=SRC_H1,
                 dev_or_heldout=split, caveats=cav + [f"{k}: {v}" for k, v in
                                                       sorted(excluded.items())],
                 prereg=PREREG, unit="runs"),
          metric("audit.heldout.h1.n_flagged", int(f.sum()), n=len(units), source=SRC_H1,
                 dev_or_heldout=split, caveats=cav, prereg=PREREG, unit="runs")]
    if f.sum() < 5 or (~f).sum() < 5:
        info["result"] = "not testable"
        ms.append(metric("audit.heldout.h1.perm_p", None, n=len(units), source=SRC_H1,
                         dev_or_heldout=split, prereg=PREREG,
                         caveats=cav + ["not testable: a group has fewer than 5 runs"]))
        return ms, info
    rng = np.random.default_rng(SEED)
    t_obs, p = stratified_perm(y, f, strata, rng)
    p_mw, rb = mwu(y, f)
    test = (f"two-sided permutation, labels permuted within idea, {N_PERM} draws, "
            f"numpy default_rng({SEED}); T = mean(passed) - mean(flagged)")
    supported = p < ALPHA and t_obs > 0
    info.update({"T": t_obs, "p": p, "mean_passed": float(y[~f].mean()),
                 "mean_flagged": float(y[f].mean()), "mwu_p": p_mw,
                 "rank_biserial": rb, "supported": supported})
    ms += [
        metric("audit.heldout.h1.mean_agreement_passed", round(float(y[~f].mean()), 4),
               n=int((~f).sum()), source=SRC_H1, dev_or_heldout=split, caveats=cav,
               prereg=PREREG),
        metric("audit.heldout.h1.mean_agreement_flagged", round(float(y[f].mean()), 4),
               n=int(f.sum()), source=SRC_H1, dev_or_heldout=split, caveats=cav,
               prereg=PREREG),
        metric("audit.heldout.h1.t_difference", round(t_obs, 4), n=len(units),
               source=SRC_H1, dev_or_heldout=split, caveats=cav, prereg=PREREG, test=test,
               description="mean agreement of passed runs minus flagged runs (H1 predicts > 0)"),
        metric("audit.heldout.h1.perm_p", round(p, 4), n=len(units), source=SRC_H1,
               dev_or_heldout=split, prereg=PREREG, test=test,
               caveats=cav + [f"H1 {'supported' if supported else 'not supported'} at alpha "
                              f"{ALPHA} (requires p < {ALPHA} and T > 0)"]),
        metric("audit.heldout.h1.supported", int(supported), n=len(units), source=SRC_H1,
               dev_or_heldout=split, prereg=PREREG, caveats=cav, unit="1 = yes, 0 = no"),
        metric("audit.heldout.h1.mwu_p", None if p_mw is None else round(p_mw, 4),
               n=len(units), source=SRC_H1, dev_or_heldout="exploratory", prereg=PREREG,
               test="two-sided Mann-Whitney U, unstratified (secondary)",
               caveats=cav + ["secondary analysis, no decision"]),
        metric("audit.heldout.h1.rank_biserial", None if rb is None else round(rb, 4),
               n=len(units), source=SRC_H1, dev_or_heldout="exploratory", prereg=PREREG,
               caveats=cav + ["secondary; positive means passed runs agree more"]),
    ]
    # secondary (b): without any run of the 19 development ideas
    keep = np.array([not u["dev_idea"] for u in units], dtype=bool)
    yb, fb = y[keep], f[keep]
    sb = [s for s, k in zip(strata, keep, strict=True) if k]
    if fb.sum() >= 5 and (~fb).sum() >= 5:
        tb, pb = stratified_perm(yb, fb, sb, np.random.default_rng(SEED))
        info["no_dev_ideas"] = {"n": int(keep.sum()), "T": tb, "p": pb}
        ms += [metric("audit.heldout.h1.no_dev_ideas.t_difference", round(tb, 4),
                      n=int(keep.sum()), source=SRC_H1, dev_or_heldout="exploratory",
                      prereg=PREREG, test=test, caveats=cav + ["secondary: runs of the 19 "
                                                               "development ideas removed"]),
               metric("audit.heldout.h1.no_dev_ideas.perm_p", round(pb, 4),
                      n=int(keep.sum()), source=SRC_H1, dev_or_heldout="exploratory",
                      prereg=PREREG, test=test, caveats=cav + ["secondary: runs of the 19 "
                                                               "development ideas removed"])]
    else:
        info["no_dev_ideas"] = {"n": int(keep.sum()), "result": "not testable",
                                "n_flagged": int(fb.sum()), "n_passed": int((~fb).sum())}
        ms.append(metric("audit.heldout.h1.no_dev_ideas.perm_p", None, n=int(keep.sum()),
                         source=SRC_H1, dev_or_heldout="exploratory", prereg=PREREG,
                         caveats=cav + ["secondary: not testable, a group has fewer than 5"]))
    # secondary (c): per code, descriptive
    per_code = {}
    for code in sorted({c for u in units for c in u["codes"]}):
        has = np.array([code in u["codes"] for u in units], dtype=bool)
        per_code[code] = {"n_with": int(has.sum()),
                          "mean_with": float(y[has].mean()) if has.any() else None,
                          "mean_without": float(y[~has].mean()) if (~has).any() else None}
    info["per_code"] = per_code
    return ms, info


def h2(frozen: bool) -> tuple[list[dict], dict]:
    rev = reviews()
    dirs = {idea_of_dir(d): d for d in example_dirs()}
    units = []
    for paper, labels in sorted(rev.items()):
        cands = [i for i in dirs if i == paper or i.endswith(paper) or i == "simple" + paper
                 or i == "basic" + paper]
        if len(cands) != 1:
            raise RuntimeError(f"paper {paper!r}: matched {cands}")
        node = audit_dir(examples_zip(), EXAMPLES_PREFIX, dirs[cands[0]])
        units.append({"paper": paper, "dir": dirs[cands[0]], "n_ratings": len(labels),
                      "soundness": soundness_score(labels), "flagged": error_flagged(node),
                      "error_codes": flagged_codes(node, ("error",))})
    y = np.array([u["soundness"] for u in units], dtype=float)
    f = np.array([u["flagged"] for u in units], dtype=bool)
    cav = ["exploratory: the 20 rated papers are the development-set directories, so this "
           "test is not blind", "outcome: mean binarised soundness (Unsound 0, other 1)"]
    if not frozen:
        cav.append("the audit rules changed after preregistration")
    info: dict = {"units": units}
    ms = [metric("audit.heldout.h2.n_papers", len(units), n=len(units), source=SRC_H2,
                 dev_or_heldout="exploratory", caveats=cav, prereg=PREREG, unit="papers"),
          metric("audit.heldout.h2.n_flagged", int(f.sum()), n=len(units), source=SRC_H2,
                 dev_or_heldout="exploratory", caveats=cav, prereg=PREREG, unit="papers")]
    if f.sum() < 3 or (~f).sum() < 3:
        ms.append(metric("audit.heldout.h2.perm_p", None, n=len(units), source=SRC_H2,
                         dev_or_heldout="exploratory", prereg=PREREG,
                         caveats=cav + ["not testable: a group has fewer than 3 papers"]))
        return ms, info
    t_obs, p = plain_perm(y, f, np.random.default_rng(SEED))
    p_mw, rb = mwu(y, f)
    test = (f"two-sided permutation, {N_PERM} draws, numpy default_rng({SEED}); "
            "T = mean(passed) - mean(flagged)")
    info.update({"T": t_obs, "p": p, "mwu_p": p_mw, "rank_biserial": rb})
    ms += [
        metric("audit.heldout.h2.mean_soundness_passed", round(float(y[~f].mean()), 4),
               n=int((~f).sum()), source=SRC_H2, dev_or_heldout="exploratory", caveats=cav,
               prereg=PREREG),
        metric("audit.heldout.h2.mean_soundness_flagged", round(float(y[f].mean()), 4),
               n=int(f.sum()), source=SRC_H2, dev_or_heldout="exploratory", caveats=cav,
               prereg=PREREG),
        metric("audit.heldout.h2.t_difference", round(t_obs, 4), n=len(units),
               source=SRC_H2, dev_or_heldout="exploratory", caveats=cav, prereg=PREREG,
               test=test),
        metric("audit.heldout.h2.perm_p", round(p, 4), n=len(units), source=SRC_H2,
               dev_or_heldout="exploratory", caveats=cav, prereg=PREREG, test=test),
        metric("audit.heldout.h2.mwu_p", None if p_mw is None else round(p_mw, 4),
               n=len(units), source=SRC_H2, dev_or_heldout="exploratory", prereg=PREREG,
               test="two-sided Mann-Whitney U (secondary)", caveats=cav),
    ]
    return ms, info


def run() -> tuple[list[dict], dict]:
    tree = rules_tree()
    frozen = tree == FROZEN_TREE
    m1, i1 = h1(frozen)
    m2, i2 = h2(frozen)
    return m1 + m2, {"rules_tree": tree, "frozen_tree": FROZEN_TREE, "frozen": frozen,
                     "frozen_commit": FROZEN_COMMIT, "h1": i1, "h2": i2}
