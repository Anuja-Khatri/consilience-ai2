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


def _perm(task: str, n: int) -> np.ndarray:
    h = hashlib.sha256(f"{SEED}:{task}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "big")).permutation(n)


def _record(task: str, target: str, pred: str, kind: str, a: tuple[float, float, int],
            b: tuple[float, float, int], control_p: float | None) -> dict[str, Any]:
    text = f"In {task}, {pred} is associated with {target}."
    quantity = f"Pearson r between {pred} and {target}"

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
        if not usable:
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

        done_targets: set[str] = set()
        for q in usable:
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
            stats_a = {c: _r(num(c)[half_a], y[half_a]) for c in planted + nulls}  # type: ignore[index]
            stats_b = {c: _r(num(c)[half_b], y[half_b]) for c in planted + nulls}  # type: ignore[index]
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
                    rows_out.append({
                        "task": task, "target": target, "column": c, "kind": kind,
                        "r_a": ra[0], "p_a": ra[1], "r_b": rb[0],
                        "full_p": full[1] if full else None,
                        "verdict": v["verdict"], "outcome": v["outcome_label"],
                        "decidability": v["decidability"],
                        "small_decidability": small["decidability"] if small else None,
                        "small_verdict": small["verdict"] if small else None,
                        "empirical_power_small": emp})
    cnt["tasks"] = len(tasks)
    return {"rows": rows_out, "counts": dict(cnt)}


def summarise(res: dict[str, Any]) -> dict[str, Any]:
    rows = res["rows"]
    out: dict[str, Any] = {"counts": res["counts"]}
    for kind in ("planted", "null"):
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
    return out


if __name__ == "__main__":
    print(json.dumps(summarise(analyse()), indent=2, sort_keys=True))
