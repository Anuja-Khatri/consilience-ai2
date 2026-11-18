"""(b) DiscoveryBench synthetic tasks: planted effects and nulls, reproduced on held-out
row halves. Label: synthetic.

Data (no network; ``consilience-ai2 fetch discoverybench``): every synthetic task
(``discoverybench/synth/{dev,test,train}/<task>/``), its ``data.csv`` and
``metadata_*.json``. Metadata that is not UTF-8 is read as cp1252 (counted).

Definitions, from the gold data and nothing else:
- A query is usable when it gives ``target_col`` and ``true_hypothesis_expr``. The
  columns named in the expression (``df['<col>']``) other than the target are the
  target's gold predictors.
- **Planted effect**: (target, a gold predictor of it). The generator wrote the target as
  a function of these columns. The function may be non-linear, so a planted effect need
  not show as a linear correlation.
- **Null**: (target, a column named by no query of the task: not a target, not in any
  gold expression, not in any ``relevant_cols``), in a task where every query is usable
  (so no undeclared relation can involve the column). The generator did not write the
  target from it. Indirect dependence through the generator cannot be excluded; the
  share of nulls that correlate with the target on all rows is reported as a check.
- Only numeric and true/false columns (true = 1) with no empty or unreadable cell and
  non-zero variance are used; other pairs are counted as skipped.

Procedure (fixed seed 0): the rows of each task are permuted (the seed per task is
derived from seed 0 and the task path by SHA-256) and split into halves. Half A is the
source: Pearson r, two-sided p, n. Half B is the reproduction. The record commits alpha
0.05, two-sided, minimum effect |r| >= 0.1, power threshold 0.8, direction = the sign
of the source r, independence axis ``cohort`` (half A vs half B). Positive control: the
target's other gold predictor with the largest |r| on half A, tested on half B (p <
alpha passes); none when the target has no other gold predictor. P1 and P2 are skipped
(records built in memory; the hypothesis text is generated identically on both sides).

Small reproductions: the same pairs, reproduced on the first 10 rows of half B. D1
should class these underpowered unless the source effect is very large. As a check on
the power formula itself, the empirical power of the same test at that size is
estimated from 200 random subsamples of half B (fixed seed) and set beside D1's class.

v0.2 additions (sensitivity and coverage; the Pearson records and verdicts above are
unchanged, and the empirical-power draws keep their order):
- **Spearman sensitivity**: every planted and null pair is also judged with Spearman's
  rho in place of Pearson's r (same halves, thresholds and procedure; the positive
  control is the other gold predictor with the largest |rho| on half A). D1's power uses
  the Fisher-z formula of type ``r`` with rho, an approximation (rho's sampling variance
  is slightly larger than r's).
- **Mutual information detection**: on half B, mutual information between the two
  columns after a fixed binning (``mi_codes``: a column with at most 4 distinct values is
  binned by value, else by its quartiles), with a permutation p from 199 permutations of
  the target's bins (seed derived from seed 0 and the pair by SHA-256). MI has no
  closed-form power, so it gives no verdict: it is reported as the share of pairs whose
  association half B detects at p < alpha, beside the same share for Pearson and Spearman.
- **Derived planted pairs** (labelled derived): a query with a natural-language gold
  hypothesis (``true_hypothesis``) but no gold expression names its columns in prose only,
  and gives no target. A column is named when its name, or its name with underscores read
  as spaces, occurs in the hypothesis as a whole word (case-insensitive). Exactly two
  named columns give one derived planted pair (association measures are symmetric, so no
  target is needed); other counts are reported and not used, since with three or more
  the pairs among predictors need not be related. Pairs already planted from a gold
  expression are not repeated. Derived pairs have no positive control.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats as st

from consilience_ai2.fetch import require
from consilience_ai2.reproduce import evaluate

SEED = 0
SMALL_N = 10
DRAWS = 200
MI_BINS = 4
MI_PERMUTATIONS = 199
THRESHOLDS = {"alpha": 0.05, "sides": 2, "minimum_effect": 0.1, "power": 0.8}
_COL = re.compile(r"""df\[\s*(['"])(?P<c>.+?)\1\s*\]""")


def _read_json(path: Path) -> tuple[dict, bool]:
    b = path.read_bytes()
    try:
        return json.loads(b.decode("utf-8")), False
    except UnicodeDecodeError:
        return json.loads(b.decode("cp1252")), True


def _numeric(values: list[str]) -> np.ndarray | None:
    out = []
    for v in values:
        s = v.strip()
        if s in ("True", "False"):
            out.append(1.0 if s == "True" else 0.0)
            continue
        try:
            x = float(s)
        except ValueError:
            return None
        if not math.isfinite(x):
            return None
        out.append(x)
    arr = np.asarray(out, dtype=float)
    return arr if arr.std() > 0 else None


def _r(x: np.ndarray, y: np.ndarray) -> tuple[float, float] | None:
    if x.std() == 0 or y.std() == 0:
        return None
    r, p = st.pearsonr(x, y)
    r = float(min(max(r, -0.999999), 0.999999))
    return r, float(p)


def _rho(x: np.ndarray, y: np.ndarray) -> tuple[float, float] | None:
    """Spearman's rho and its two-sided p (None for a constant column)."""
    if x.std() == 0 or y.std() == 0:
        return None
    res = st.spearmanr(x, y)
    rho, p = float(res.statistic), float(res.pvalue)
    if not (math.isfinite(rho) and math.isfinite(p)):
        return None
    return float(min(max(rho, -0.999999), 0.999999)), p


def mi_codes(x: np.ndarray, bins: int = MI_BINS) -> np.ndarray:
    """Fixed binning for mutual information: by value when the column has at most
    ``bins`` distinct values, else by its quartiles (``bins`` equal-frequency bins; ties
    may merge bins)."""
    u = np.unique(x)
    if len(u) <= bins:
        return np.searchsorted(u, x)
    edges = np.quantile(x, [i / bins for i in range(1, bins)])
    return np.searchsorted(edges, x, side="right")


def mutual_information(a: np.ndarray, b: np.ndarray) -> float:
    """Mutual information (nats) of two integer-coded columns."""
    ka, kb = int(a.max()) + 1, int(b.max()) + 1
    joint = np.bincount(a * kb + b, minlength=ka * kb).reshape(ka, kb) / len(a)
    pa, pb = joint.sum(1), joint.sum(0)
    nz = joint > 0
    return float((joint[nz] * np.log(joint[nz] / np.outer(pa, pb)[nz])).sum())


def mi_test(x: np.ndarray, y: np.ndarray, key: str) -> tuple[float, float]:
    """Mutual information of the binned columns and its permutation p (the target's
    bins permuted ``MI_PERMUTATIONS`` times; seed from ``key`` by SHA-256)."""
    a, b = mi_codes(x), mi_codes(y)
    obs = mutual_information(a, b)
    h = hashlib.sha256(f"{SEED}:mi:{key}".encode()).digest()
    rng = np.random.default_rng(int.from_bytes(h[:8], "big"))
    hits = sum(mutual_information(a, rng.permutation(b)) >= obs - 1e-12
               for _ in range(MI_PERMUTATIONS))
    return obs, (1 + hits) / (1 + MI_PERMUTATIONS)


def named_columns(text: str, columns: list[str]) -> list[str]:
    """Columns named in a natural-language hypothesis: the name, or the name with
    underscores read as spaces, as a whole word, case-insensitive. In column order."""
    t = (text or "").casefold()
    out = []
    for c in columns:
        forms = {c.casefold(), c.casefold().replace("_", " ")}
        if any(f.strip() and re.search(r"(?<![a-z0-9_])" + re.escape(f) + r"(?![a-z0-9_])", t)
               for f in forms):
            out.append(c)
    return out


def _perm(task: str, n: int) -> np.ndarray:
    h = hashlib.sha256(f"{SEED}:{task}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "big")).permutation(n)


def _record(task: str, target: str, pred: str, kind: str, a: tuple[float, float, int],
            b: tuple[float, float, int], control_p: float | None,
            measure: str = "Pearson r") -> dict[str, Any]:
    text = f"In {task}, {pred} is associated with {target}."
    quantity = f"{measure} between {pred} and {target}"

    def meas(x: tuple[float, float, int], half: str) -> dict[str, Any]:
        r, p, n = x
        return {"quantity": quantity, "value": r, "unit": "dimensionless", "n": n, "p": p,
                "effect_size": {"type": "r", "value": r}, "conditions": {"cohort": half}}

    rec = {"schema_version": 1, "id": f"{task}:{target}~{pred}:{kind}", "hypothesis": text,
           "source_hypothesis": text, "source": meas(a, "half A"),
           "reproduction": meas(b, "half B"), "quantity_mapping": {"relation": "same_quantity"},
           "independence_axis": "cohort", "thresholds": dict(THRESHOLDS)}
    if control_p is not None:
        rec["positive_control"] = {"p": control_p}
    return rec


def _sensitivity(task: str, target: str, c: str, kind: str, x: np.ndarray, y: np.ndarray,
                 half_a: np.ndarray, half_b: np.ndarray, rho_a: dict, rho_b: dict,
                 controls: list[str], pearson_p_b: float) -> dict[str, Any]:
    """The Spearman verdict and the half-B detections (Pearson, Spearman, MI) of a pair."""
    out: dict[str, Any] = {"pearson_p_b": pearson_p_b}
    sa, sb = rho_a.get(c), rho_b.get(c)
    if sa is None or sb is None:
        out.update(s_verdict=None, s_outcome=None, s_decidability=None, spearman_p_b=None)
    else:
        others = [o for o in controls if o != c and rho_a.get(o) is not None
                  and rho_b.get(o) is not None]
        ctrl = max(others, key=lambda o: (abs(rho_a[o][0]), o)) if others else None
        cp = rho_b[ctrl][1] if ctrl else None
        sv = evaluate(_record(task, target, c, kind, (sa[0], sa[1], len(half_a)),
                              (sb[0], sb[1], len(half_b)), cp, measure="Spearman rho"),
                      backend="fallback", skip=("P1", "P2")).extra["verdict"]
        out.update(s_verdict=sv["verdict"], s_outcome=sv["outcome_label"],
                   s_decidability=sv["decidability"], spearman_p_b=sb[1])
    out["mi_p_b"] = mi_test(x[half_b], y[half_b], f"{task}:{target}:{c}")[1]
    return out


def _derived(task: str, prose: list[dict], header: list[str], num, half_a: np.ndarray,
             half_b: np.ndarray, planted_here: set, cnt: Counter) -> list[dict[str, Any]]:
    """Derived planted pairs from gold hypotheses in prose (see the module docstring)."""
    out = []
    done: set[frozenset[str]] = set()
    for q in prose:
        named = named_columns(q["true_hypothesis"], header)
        cnt[f"derived_named_{min(len(named), 3)}{'+' if len(named) >= 3 else ''}"] += 1
        if len(named) != 2:
            continue
        pair = frozenset(named)
        if pair in planted_here or pair in done:
            cnt["derived_skipped_already_planted_or_repeated"] += 1
            continue
        done.add(pair)
        a_col, b_col = sorted(named)
        x, y = num(a_col), num(b_col)
        if x is None or y is None:
            cnt["derived_skipped_not_numeric"] += 1
            continue
        ra, rb = _r(x[half_a], y[half_a]), _r(x[half_b], y[half_b])
        if ra is None or rb is None:
            cnt["derived_skipped_constant_in_a_half"] += 1
            continue
        v = evaluate(_record(task, b_col, a_col, "derived", (ra[0], ra[1], len(half_a)),
                             (rb[0], rb[1], len(half_b)), None),
                     backend="fallback", skip=("P1", "P2")).extra["verdict"]
        rho = {a_col: (_rho(x[half_a], y[half_a]), _rho(x[half_b], y[half_b]))}
        sens = _sensitivity(task, b_col, a_col, "derived", x, y, half_a, half_b,
                            {a_col: rho[a_col][0]}, {a_col: rho[a_col][1]}, [], rb[1])
        full = _r(x, y)
        out.append({"task": task, "target": b_col, "column": a_col, "kind": "derived",
                    "r_a": ra[0], "p_a": ra[1], "r_b": rb[0],
                    "full_p": full[1] if full else None,
                    "verdict": v["verdict"], "outcome": v["outcome_label"],
                    "decidability": v["decidability"], "small_decidability": None,
                    "small_verdict": None, "empirical_power_small": None, **sens})
    return out


def analyse() -> dict[str, Any]:
    root = require("discoverybench") / "discoverybench" / "synth"
    tasks = sorted(p.parent for p in root.glob("*/*/data.csv"))
    cnt: Counter = Counter()
    rows_out: list[dict[str, Any]] = []
    rng_emp = np.random.default_rng(SEED)
    for tdir in tasks:
        task = tdir.relative_to(root).as_posix()
        queries = []
        for mp in sorted(tdir.glob("metadata_*.json")):
            md, cp = _read_json(mp)
            cnt["metadata_cp1252"] += cp
            queries.extend(md.get("queries", []))
        cnt["queries"] += len(queries)
        usable = [q for q in queries if q.get("target_col") and q.get("true_hypothesis_expr")]
        cnt["queries_usable"] += len(usable)
        prose = [q for q in queries if not q.get("true_hypothesis_expr")
                 and (q.get("true_hypothesis") or "").strip()]
        cnt["queries_gold_text_only"] += len(prose)
        cnt["queries_no_gold"] += sum(1 for q in queries if not q.get("true_hypothesis_expr")
                                      and not (q.get("true_hypothesis") or "").strip())
        if not usable and not prose:
            continue
        with (tdir / "data.csv").open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            raw = list(reader)
        cols = {h: [row[i] if i < len(row) else "" for row in raw] for i, h in enumerate(header)}
        mentioned: set[str] = set()
        for q in queries:
            mentioned.add(q.get("target_col") or "")
            mentioned.update(q.get("relevant_cols") or [])
            mentioned.update(m.group("c") for m in _COL.finditer(q.get("true_hypothesis_expr") or ""))
        all_usable = len(usable) == len(queries)
        n = len(raw)
        perm = _perm(task, n)
        half_a, half_b = perm[: n // 2], perm[n // 2:]
        numeric: dict[str, np.ndarray | None] = {c: _numeric(v) for c, v in cols.items()}
        num = numeric.get
        planted_here: set[frozenset[str]] = set()

        done_targets: set[str] = set()
        for q in usable:  # (a task without usable queries has none: the loop is empty)
            target = q["target_col"]
            if target in done_targets:
                continue
            done_targets.add(target)
            gold = sorted({m.group("c") for m in _COL.finditer(q["true_hypothesis_expr"])}
                          - {target})
            y = num(target)
            if y is None:
                cnt["skipped_target_not_numeric"] += 1
                continue
            planted = []
            for c in gold:
                if c not in cols:
                    cnt["skipped_planted_unknown_column"] += 1
                elif num(c) is None:
                    cnt["skipped_planted_not_numeric"] += 1
                else:
                    planted.append(c)
            nulls = []
            if all_usable:
                for c in header:
                    if c in mentioned:
                        continue
                    if num(c) is None:
                        cnt["skipped_null_not_numeric"] += 1
                    else:
                        nulls.append(c)
            else:
                cnt["targets_without_nulls_(task_has_unusable_queries)"] += 1
            planted_here.update(frozenset((target, c)) for c in planted)
            stats_a = {c: _r(num(c)[half_a], y[half_a]) for c in planted + nulls}  # type: ignore[index]
            stats_b = {c: _r(num(c)[half_b], y[half_b]) for c in planted + nulls}  # type: ignore[index]
            rho_a = {c: _rho(num(c)[half_a], y[half_a]) for c in planted + nulls}  # type: ignore[index]
            rho_b = {c: _rho(num(c)[half_b], y[half_b]) for c in planted + nulls}  # type: ignore[index]
            for kind, group in (("planted", planted), ("null", nulls)):
                for c in group:
                    ra, rb = stats_a[c], stats_b[c]
                    if ra is None or rb is None:
                        cnt[f"skipped_{kind}_constant_in_a_half"] += 1
                        continue
                    others = [o for o in planted if o != c and stats_a[o] is not None
                              and stats_b[o] is not None]
                    ctrl = max(others, key=lambda o: (abs(stats_a[o][0]), o)) if others else None
                    cp = stats_b[ctrl][1] if ctrl else None
                    a = (ra[0], ra[1], len(half_a))
                    b = (rb[0], rb[1], len(half_b))
                    v = evaluate(_record(task, target, c, kind, a, b, cp), backend="fallback",
                                 skip=("P1", "P2")).extra["verdict"]
                    # small reproduction: first SMALL_N rows of half B
                    xs, ys = num(c)[half_b[:SMALL_N]], y[half_b[:SMALL_N]]  # type: ignore[index]
                    rs = _r(xs, ys)
                    small = None
                    emp = None
                    if rs is not None:
                        small = evaluate(
                            _record(task, target, c, kind, a, (rs[0], rs[1], SMALL_N), cp),
                            backend="fallback", skip=("P1", "P2")).extra["verdict"]
                        hits = 0
                        xb, yb = num(c)[half_b], y[half_b]  # type: ignore[index]
                        sign = 1 if ra[0] > 0 else -1
                        for _ in range(DRAWS):
                            idx = rng_emp.choice(len(half_b), SMALL_N, replace=False)
                            r2 = _r(xb[idx], yb[idx])
                            if r2 is not None and r2[1] < THRESHOLDS["alpha"] and \
                                    sign * r2[0] > 0:
                                hits += 1
                        emp = hits / DRAWS
                    full = _r(num(c), y)  # type: ignore[arg-type]
                    sens = _sensitivity(task, target, c, kind, num(c), y, half_a, half_b,
                                        rho_a, rho_b, planted, rb[1])
                    rows_out.append({
                        "task": task, "target": target, "column": c, "kind": kind,
                        "r_a": ra[0], "p_a": ra[1], "r_b": rb[0],
                        "full_p": full[1] if full else None,
                        "verdict": v["verdict"], "outcome": v["outcome_label"],
                        "decidability": v["decidability"],
                        "small_decidability": small["decidability"] if small else None,
                        "small_verdict": small["verdict"] if small else None,
                        "empirical_power_small": emp, **sens})
        rows_out.extend(_derived(task, prose, header, num, half_a, half_b, planted_here, cnt))
    cnt["tasks"] = len(tasks)
    return {"rows": rows_out, "counts": dict(cnt)}


def summarise(res: dict[str, Any]) -> dict[str, Any]:
    rows = res["rows"]
    out: dict[str, Any] = {"counts": res["counts"]}
    for kind in ("planted", "null", "derived"):
        g = [r for r in rows if r["kind"] == kind]
        small = [r for r in g if r["small_decidability"] is not None]
        out[kind] = {
            "n": len(g),
            "verdict": dict(Counter(r["verdict"] for r in g)),
            "outcome": dict(Counter(r["outcome"] for r in g)),
            "decidability": dict(Counter(r["decidability"] for r in g)),
            "n_small": len(small),
            "small_decidability": dict(Counter(r["small_decidability"] for r in small)),
            "small_verdict": dict(Counter(r["small_verdict"] for r in small)),
            # D1 class vs empirical power (>= 0.8) at the small size
            "small_vs_empirical": dict(Counter(
                f"{r['small_decidability']}|{'emp>=0.8' if r['empirical_power_small'] >= 0.8 else 'emp<0.8'}"
                for r in small if r["small_decidability"] in ("decidable", "underpowered"))),
            "full_data_significant": sum(1 for r in g if r["full_p"] is not None
                                         and r["full_p"] < 0.05),
            # verdicts among pairs whose source half itself found the effect (p < alpha)
            "source_significant_verdict": dict(Counter(
                r["verdict"] for r in g if r["p_a"] < THRESHOLDS["alpha"])),
            "decidable_verdict": dict(Counter(
                r["verdict"] for r in g if r["decidability"] == "decidable")),
            "reproduced_full_data_significant": sum(
                1 for r in g if r["verdict"] == "reproduced" and r["full_p"] is not None
                and r["full_p"] < 0.05),
        }
        # v0.2 sensitivity: Spearman verdicts and half-B detections
        sp = [r for r in g if r["s_verdict"] is not None]
        alpha = THRESHOLDS["alpha"]
        out[kind]["spearman"] = {
            "n": len(sp),
            "verdict": dict(Counter(r["s_verdict"] for r in sp)),
            "outcome": dict(Counter(r["s_outcome"] for r in sp)),
            "decidability": dict(Counter(r["s_decidability"] for r in sp)),
            "decidable_verdict": dict(Counter(r["s_verdict"] for r in sp
                                              if r["s_decidability"] == "decidable")),
        }
        out[kind]["detected_b"] = {
            "n": len(g),
            "pearson": sum(1 for r in g if r["pearson_p_b"] < alpha),
            "spearman": sum(1 for r in g if r["spearman_p_b"] is not None
                            and r["spearman_p_b"] < alpha),
            "mi": sum(1 for r in g if r["mi_p_b"] < alpha),
            "mi_not_pearson": sum(1 for r in g if r["mi_p_b"] < alpha
                                  and not r["pearson_p_b"] < alpha),
        }
    return out


if __name__ == "__main__":
    print(json.dumps(summarise(analyse()), indent=2, sort_keys=True))
