"""Metric records, per-component results files and the merged registry.

Every number this project reports is a metric record in ``results/<component>.json``
(written with ``write_results``). ``build_registry`` merges every component file into
``results/registry.json``; the numbers lock (``scripts/numbers_lock.py``) then checks
that each result-like number in the docs renders from the registry.

A metric record has exactly these required fields:

``metric_id``       ``"<component>.<name>"``: lowercase, digits, ``_ . -``; unique.
``value``           a finite int or float, or None when not measured (then ``caveats``
                    must say why). Booleans are refused.
``n``               the sample size behind the value (int >= 0), or None.
``ci_lo, ci_hi``    a confidence interval (both or neither), ``ci_lo <= ci_hi``.
``source``          what it was computed from, e.g. ``"fetch:theorizer-paper-data"``.
``caveats``         a list of strings (may be empty).
``dev_or_heldout``  one of ``SPLITS``: ``dev`` (rules written knowing the data),
                    ``heldout`` (preregistered before scoring), ``exploratory``
                    (labelled as such), ``descriptive`` (a measured rate, no hypothesis),
                    ``synthetic`` (on planted fixtures, true by construction).

and may carry these optional fields: ``unit``, ``description``, ``test`` (the stated
statistical test), ``prereg`` (path and commit of the preregistration), ``receipts``
(a path or list of example receipts). Unknown fields are refused.

Files are written deterministically (sorted metrics and keys, two-space indent, final
newline), so re-running an analysis on the same data gives the same bytes.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from consilience_ai2.core.hashing import sha256_file, sha256_json

SCHEMA_VERSION = 1
SPLITS = ("dev", "heldout", "exploratory", "descriptive", "synthetic")
REQUIRED = ("metric_id", "value", "n", "ci_lo", "ci_hi", "source", "caveats", "dev_or_heldout")
OPTIONAL = ("unit", "description", "test", "prereg", "receipts")
REGISTRY_NAME = "registry.json"
LOCK_NAME = "NUMBERS_LOCK.json"
NOT_COMPONENT_FILES = frozenset({REGISTRY_NAME, LOCK_NAME})
_COMPONENT = re.compile(r"^[a-z][a-z0-9_]*$")
_METRIC_TAIL = re.compile(r"^[a-z0-9_][a-z0-9_.\-]*$")


class ResultsError(ValueError):
    """A results file or metric record that does not meet the schema."""


def _is_number(v: Any) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)


def metric(metric_id: str, value: float | int | None, *, n: int | None, source: str,
           dev_or_heldout: str, ci_lo: float | None = None, ci_hi: float | None = None,
           caveats: Iterable[str] = (), **optional: Any) -> dict[str, Any]:
    """Build one metric record (validated against its own component prefix)."""
    if isinstance(caveats, str):
        raise ResultsError(f"{metric_id}: caveats must be a list of strings, not one string")
    rec: dict[str, Any] = {
        "metric_id": metric_id, "value": value, "n": n, "ci_lo": ci_lo, "ci_hi": ci_hi,
        "source": source, "caveats": list(caveats), "dev_or_heldout": dev_or_heldout,
    }
    rec.update(optional)
    validate_metric(rec, metric_id.split(".", 1)[0])
    return rec


def validate_metric(m: Mapping[str, Any], component: str) -> None:
    """Raise ``ResultsError`` unless ``m`` is a valid record of ``component``."""
    mid = m.get("metric_id", "<missing>")
    missing = [k for k in REQUIRED if k not in m]
    if missing:
        raise ResultsError(f"{mid}: missing fields {missing}")
    unknown = sorted(set(m) - set(REQUIRED) - set(OPTIONAL))
    if unknown:
        raise ResultsError(f"{mid}: unknown fields {unknown} (allowed extras: {OPTIONAL})")
    if not isinstance(mid, str) or not mid.startswith(component + "."):
        raise ResultsError(f"{mid}: metric_id must start with '{component}.'")
    if not _METRIC_TAIL.match(mid[len(component) + 1:]):
        raise ResultsError(f"{mid}: metric_id tail must match {_METRIC_TAIL.pattern}")
    v = m["value"]
    if v is None:
        if not m["caveats"]:
            raise ResultsError(f"{mid}: value is None, so caveats must say why")
    elif not _is_number(v):
        raise ResultsError(f"{mid}: value must be a finite number or None, got {v!r}")
    n = m["n"]
    if n is not None and (not isinstance(n, int) or isinstance(n, bool) or n < 0):
        raise ResultsError(f"{mid}: n must be an int >= 0 or None, got {n!r}")
    lo, hi = m["ci_lo"], m["ci_hi"]
    if (lo is None) != (hi is None):
        raise ResultsError(f"{mid}: give both ci_lo and ci_hi, or neither")
    if lo is not None:
        if not (_is_number(lo) and _is_number(hi)):
            raise ResultsError(f"{mid}: ci bounds must be finite numbers")
        if lo > hi:
            raise ResultsError(f"{mid}: ci_lo > ci_hi")
    if not isinstance(m["source"], str) or not m["source"].strip():
        raise ResultsError(f"{mid}: source must be a non-empty string")
    cav = m["caveats"]
    if not isinstance(cav, list) or not all(isinstance(c, str) for c in cav):
        raise ResultsError(f"{mid}: caveats must be a list of strings")
    if m["dev_or_heldout"] not in SPLITS:
        raise ResultsError(f"{mid}: dev_or_heldout must be one of {SPLITS}")


def _dump(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def write_results(component: str, metrics: Iterable[Mapping[str, Any]],
                  results_dir: str | Path = "results") -> Path:
    """Write ``results/<component>.json`` (validated, sorted, deterministic)."""
    if not _COMPONENT.match(component):
        raise ResultsError(f"component name must match {_COMPONENT.pattern}: {component!r}")
    recs = [dict(m) for m in metrics]
    for m in recs:
        validate_metric(m, component)
    ids = [m["metric_id"] for m in recs]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ResultsError(f"duplicate metric_id {dupes}")
    data = {"schema_version": SCHEMA_VERSION, "component": component,
            "metrics": sorted(recs, key=lambda r: r["metric_id"])}
    path = Path(results_dir) / f"{component}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(data), encoding="utf-8")
    return path


def load_results(path: str | Path) -> dict[str, Any]:
    """Load and validate one component results file."""
    p = Path(path)
    component = p.stem
    if not _COMPONENT.match(component):
        raise ResultsError(f"{p.name}: results files are named <component>.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ResultsError(f"{p.name}: schema_version must be {SCHEMA_VERSION}")
    if data.get("component") != component:
        raise ResultsError(f"{p.name}: 'component' must equal the file stem {component!r}")
    for m in data.get("metrics", []):
        validate_metric(m, component)
    return data


def component_files(results_dir: str | Path) -> list[Path]:
    """The component results files in ``results_dir`` (not the registry or the lock)."""
    return sorted(p for p in Path(results_dir).glob("*.json") if p.name not in NOT_COMPONENT_FILES)


def build_registry(results_dir: str | Path = "results") -> dict[str, Any]:
    """Merge every ``results/<component>.json`` into one registry dict."""
    components: dict[str, Any] = {}
    metrics: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for p in component_files(results_dir):
        data = load_results(p)
        comp = data["component"]
        for m in data["metrics"]:
            if m["metric_id"] in seen:
                raise ResultsError(f"{m['metric_id']} in both {seen[m['metric_id']]} and {p.name}")
            seen[m["metric_id"]] = p.name
            metrics.append(dict(m))
        components[comp] = {"file": f"results/{p.name}", "sha256": sha256_file(p),
                            "n_metrics": len(data["metrics"])}
    metrics.sort(key=lambda r: r["metric_id"])
    return {"schema_version": SCHEMA_VERSION, "components": components, "metrics": metrics,
            "metrics_sha256": metrics_sha256(metrics)}


def metrics_sha256(metrics: Iterable[Mapping[str, Any]]) -> str:
    """SHA-256 of the canonical JSON of the metrics, sorted by ``metric_id``."""
    return sha256_json(sorted((dict(m) for m in metrics), key=lambda r: r["metric_id"]))


def registry_text(results_dir: str | Path = "results") -> str:
    return _dump(build_registry(results_dir))


def write_registry(results_dir: str | Path = "results") -> Path:
    """Build and write ``results/registry.json``; return its path."""
    path = Path(results_dir) / REGISTRY_NAME
    path.write_text(registry_text(results_dir), encoding="utf-8")
    return path
