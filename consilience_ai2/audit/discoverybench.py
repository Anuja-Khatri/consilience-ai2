"""DiscoveryBench adapter for A5: a fixed scan of every column against a task's target.

A DiscoveryBench synthetic task is a directory with ``data.csv`` and one or more
``metadata_<k>.json`` files; each metadata file holds one query. Some queries carry a
machine-readable gold relation (``target_col``, ``relevant_cols``,
``true_hypothesis_expr``); the others carry only a natural-language hypothesis.

The scan (deterministic, documented in docs/audit.md):

- Column types: ``constant`` (one distinct non-missing value: untestable), ``binary``
  (exactly two distinct values), ``numeric`` (every non-missing value parses as a number
  and there are more than two distinct values), ``identifier`` (a non-numeric column with
  more distinct values than half its non-missing rows: untestable), else ``categorical``.
- Tests, two-sided, on pairwise-complete rows (at least ``MIN_ROWS``):
  numeric-numeric: Spearman rank correlation; binary-numeric: point-biserial correlation
  (the binary coded 0/1 by sorted level); categorical-numeric: Kruskal-Wallis across
  levels; binary or categorical against binary or categorical: chi-square test of
  independence on the contingency table (no continuity correction).
- Benjamini-Hochberg within each task over every tested column.

Nothing here is random. ``permuted_target`` gives a null control: the same scan against
a copy of the target shuffled with ``numpy.random.default_rng(seed)``.

Derived gold (``derive_gold``, rules v0.2), for queries without a machine-readable gold
relation. A fixed rule, no language model: text is lower-cased and every run of
characters other than ``a-z0-9`` becomes one space, in both the text and the column names
(``conflict_ratio`` -> ``conflict ratio``). A column is *mentioned* when its normalised
name occurs in the normalised question or gold hypothesis as whole words; a shorter name
that occurs only inside a mention of a longer column name does not count. The derived
target is the column mentioned first in the question (else first in the hypothesis); the
derived gold columns are every other mentioned column. A query is usable when it has a
derived target and at least one derived gold column. Agreement with the machine-readable
relation, where both exist, is reported beside the derived results.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from scipy import stats as sps

from consilience_ai2.audit.stats import benjamini_hochberg

MIN_ROWS = 10
MISSING = {"", "na", "nan", "none", "null", "n/a"}


@dataclass
class Task:
    task_id: str
    split: str
    metadata_path: Path
    csv_path: Path
    target: str | None
    relevant: list[str]
    columns_meta: list[str]
    has_structured_gold: bool
    question: str = ""
    hypothesis: str = ""


@dataclass
class ColumnTest:
    column: str
    kind: str          # gold / distractor
    test: str | None
    p: float | None
    n: int
    q: float | None = None
    skipped: str | None = None


@dataclass
class TaskScan:
    task: Task
    target_type: str
    tests: list[ColumnTest] = field(default_factory=list)
    excluded: str | None = None


def _read_json(p: Path) -> dict:
    b = p.read_bytes()
    try:
        return json.loads(b.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(b.decode("cp1252"))


def load_task(metadata_path: Path, split: str) -> Task:
    m = _read_json(metadata_path)
    q = (m.get("queries") or [{}])[0]
    ds = (m.get("datasets") or [{}])[0]
    cols = [c["name"] for c in ds.get("columns", []) if isinstance(c, dict) and "name" in c]
    target = q.get("target_col")
    rel = list(q.get("relevant_cols") or [])
    tid = f"{split}/{metadata_path.parent.name}/{metadata_path.stem}"
    return Task(tid, split, metadata_path, metadata_path.parent / ds.get("name", "data.csv"),
                target, rel, cols, bool(target and rel), question=q.get("question") or "",
                hypothesis=q.get("true_hypothesis") or "")


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalise_words(text: str) -> str:
    """Lower case, every run of non-alphanumerics one space, padded with spaces."""
    return " " + _NON_ALNUM.sub(" ", text.lower()).strip() + " "


def mentions(text: str, columns: list[str]) -> list[tuple[int, str]]:
    """(first position, column) of every column whose normalised name occurs in ``text`` as
    whole words, longest names first when claiming text; sorted by position."""
    t = normalise_words(text)
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []
    for col in sorted(set(columns), key=lambda c: (-len(normalise_words(c)), c)):
        phrase = normalise_words(col)
        if phrase.strip() == "":
            continue
        first = None
        start = t.find(phrase)
        while start != -1:
            span = (start, start + len(phrase))
            if not any(a <= span[0] and span[1] <= b for a, b in taken):
                first = start if first is None else first
                taken.append(span)
            start = t.find(phrase, start + 1)
        if first is not None:
            found.append((first, col))
    return sorted(found)


@dataclass(frozen=True)
class DerivedGold:
    target: str | None
    relevant: list[str]          # derived gold columns (target excluded)
    in_question: list[str]
    in_hypothesis: list[str]

    @property
    def usable(self) -> bool:
        return self.target is not None and bool(self.relevant)


def derive_gold(task: Task) -> DerivedGold:
    """The documented rule above: target = first column mentioned in the question (else in
    the hypothesis), gold = the other mentioned columns."""
    cols = task.columns_meta
    q = [c for _, c in mentions(task.question, cols)]
    h = [c for _, c in mentions(task.hypothesis, cols)]
    target = q[0] if q else (h[0] if h else None)
    rel = [c for c in dict.fromkeys(q + h) if c != target]
    return DerivedGold(target, rel, q, h)


def with_derived_gold(task: Task, dg: DerivedGold) -> Task:
    """A copy of ``task`` whose target and relevant columns are the derived ones."""
    return replace(task, target=dg.target, relevant=[dg.target, *dg.relevant] if dg.target
                   else list(dg.relevant), has_structured_gold=False)


def read_csv(path: Path) -> dict[str, list[str]]:
    b = path.read_bytes()
    try:
        text = b.decode("utf-8")
    except UnicodeDecodeError:
        text = b.decode("cp1252")
    rows = list(csv.reader(text.splitlines()))
    header = rows[0]
    out: dict[str, list[str]] = {h: [] for h in header}
    for r in rows[1:]:
        for i, h in enumerate(header):
            out[h].append(r[i] if i < len(r) else "")
    return out


def _num(v: str) -> float | None:
    try:
        x = float(v)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def column_type(values: list[str]) -> str:
    present = [v for v in values if v.strip().lower() not in MISSING]
    distinct = set(present)
    if len(distinct) <= 1:
        return "constant"
    if len(distinct) == 2:
        return "binary"
    if all(_num(v) is not None for v in present):
        return "numeric"
    if len(distinct) > len(present) / 2:
        return "identifier"
    return "categorical"


def pair_test(x: list[str], tx: str, y: list[str], ty: str) -> tuple[str | None, float | None,
                                                                         int, str | None]:
    """(test name, p, n rows, reason skipped) for column x against target y."""
    if tx in ("constant", "identifier") or ty in ("constant", "identifier"):
        return None, None, 0, f"untestable type ({tx} vs {ty})"
    rows = [(a, b) for a, b in zip(x, y, strict=True)
            if a.strip().lower() not in MISSING and b.strip().lower() not in MISSING]
    n = len(rows)
    if n < MIN_ROWS:
        return None, None, n, "fewer than MIN_ROWS complete rows"
    xs, ys = [a for a, _ in rows], [b for _, b in rows]
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None, None, n, "constant on complete rows"
    if tx == "numeric" and ty == "numeric":
        r = sps.spearmanr([float(a) for a in xs], [float(b) for b in ys])
        return "spearman", float(r.pvalue), n, None
    if {tx, ty} == {"binary", "numeric"}:
        bin_v, num_v = (xs, ys) if tx == "binary" else (ys, xs)
        levels = sorted(set(bin_v))
        r = sps.pointbiserialr([levels.index(v) for v in bin_v], [float(v) for v in num_v])
        return "point-biserial", float(r.pvalue), n, None
    if {tx, ty} == {"categorical", "numeric"}:
        cat_v, num_v = (xs, ys) if tx == "categorical" else (ys, xs)
        groups: dict[str, list[float]] = {}
        for c, v in zip(cat_v, num_v, strict=True):
            groups.setdefault(c, []).append(float(v))
        gs = [g for _, g in sorted(groups.items()) if len(g) >= 1]
        if len(gs) < 2:
            return None, None, n, "fewer than two groups"
        try:
            r = sps.kruskal(*gs)
        except ValueError:
            return None, None, n, "kruskal undefined (all values identical)"
        return "kruskal-wallis", float(r.pvalue), n, None
    # both binary/categorical
    lx, ly = sorted(set(xs)), sorted(set(ys))
    table = np.zeros((len(lx), len(ly)))
    for a, b in rows:
        table[lx.index(a), ly.index(b)] += 1
    chi = sps.chi2_contingency(table, correction=False)
    return "chi-square", float(chi.pvalue), n, None


def scan_task(task: Task, data: dict[str, list[str]], target_values: list[str] | None = None
              ) -> TaskScan:
    """Every column of ``data`` (except the target) against the target, then BH."""
    if not task.target or task.target not in data:
        return TaskScan(task, "missing", excluded="target column not in the CSV")
    y = target_values if target_values is not None else data[task.target]
    ty = column_type(y)
    if ty in ("constant", "identifier"):
        return TaskScan(task, ty, excluded=f"target is {ty}")
    sc = TaskScan(task, ty)
    gold = set(task.relevant) - {task.target}
    for col in sorted(data):
        if col == task.target:
            continue
        x = data[col]
        tx = column_type(x)
        test, p, n, why = pair_test(x, tx, y, ty)
        sc.tests.append(ColumnTest(col, "gold" if col in gold else "distractor", test, p, n,
                                   skipped=why))
    tested = [t for t in sc.tests if t.p is not None]
    for t, q in zip(tested, benjamini_hochberg([t.p for t in tested]), strict=True):
        t.q = q
    return sc


def permuted_target(values: list[str], seed: int) -> list[str]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(values))
    return [values[i] for i in idx]


def tasks(root: Path) -> list[Task]:
    """Every synthetic task (``synth/<split>/<dataset>/metadata_<k>.json``), sorted."""
    out = []
    for split in ("train", "dev", "test"):
        for p in sorted((root / "discoverybench" / "synth" / split).glob("*/metadata_*.json")):
            out.append(load_task(p, split))
    return out
