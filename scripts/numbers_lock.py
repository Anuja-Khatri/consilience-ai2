#!/usr/bin/env python3
"""Numbers lock: every result-like number in the docs must render from the registry.

Pattern from lab-gate (eval/numbers_lock.py), adapted to per-component results files.

``lock``     Build ``results/registry.json`` from ``results/<component>.json``, render the
             results table (``docs/tables/results.md``) and write
             ``results/NUMBERS_LOCK.json`` with the SHA-256 of the metrics. The integrator
             runs this (``make lock``) after merging the component branches.
``--check``  (CI) 1. the lock hash matches the committed registry; 2. the committed table
             is a fresh render of it; 3. the committed registry equals a fresh merge of the
             component files (a warning on a component branch, an error with
             ``--strict``); 4. every result-like token in the scanned docs is derivable
             from the merged registry or allow-listed. Any failure exits 1.

What is scanned: README.md, CHANGELOG.md, docs/**/*.md (not the rendered table, which
is byte-checked instead), analyses/**/*.md and plugins/**/*.md. Not scanned: prereg/
(written before any result exists) and examples/ (synthetic fixtures with planted
numbers).

What is result-like: decimals (``0.42``) and percentages (``42%``, ``7.9%``), as in
lab-gate.
Integers are counts or identifiers and are not scanned. Before scanning, identifiers are
removed: URLs, DOIs, arXiv ids (``arXiv:2503.22708`` and bare ``2503.22708``), hex
hashes, version strings (``0.1.0``, ``v1.2``, ``Python 3.11``), licence names
(``Apache-2.0``) and section marks (``§4.2``). A number glued to a letter (``e595.3``,
``F1``) is an identifier, not a result.

Allow-lists: ``scripts/numbers_allowlist/*.txt``, one token per line, ``#`` comments.
``core.txt`` is shared; each component adds its own ``<component>.txt`` for structural
constants (thresholds such as 0.05, margins) that are not results.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from consilience_ai2.core.results import (  # noqa: E402
    LOCK_NAME,
    REGISTRY_NAME,
    build_registry,
    metrics_sha256,
    registry_text,
)

RESULTS = REPO / "results"
REGISTRY = RESULTS / REGISTRY_NAME
LOCK = RESULTS / LOCK_NAME
TABLE = REPO / "docs" / "tables" / "results.md"
ALLOW_DIR = REPO / "scripts" / "numbers_allowlist"
SCAN_FILES = ["README.md", "CHANGELOG.md"]
SCAN_GLOBS = ["docs/**/*.md", "analyses/**/*.md", "plugins/**/*.md"]

_NUM = re.compile(r"(?<![\w.])(?:\d+(?:\.\d+)?%|\d+\.\d+)")
_IDENTIFIERS = [
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\bdoi:\s*\S+|\b10\.\d{4,9}/\S+", re.IGNORECASE),
    re.compile(r"\barXiv:?\s*\d{4}\.\d{4,5}(?:v\d+)?", re.IGNORECASE),
    re.compile(r"(?<![\d.])\d{4}\.\d{4,5}(?:v\d+)?(?![\d.])"),
    re.compile(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,64}\b"),
    re.compile(r"\bsha256:\s*[0-9a-f]+", re.IGNORECASE),
    re.compile(r"\bv\d+(?:\.\d+)+"),
    re.compile(r"\b\d+\.\d+\.\d+(?:\.\d+)*\b"),
    re.compile(r"\bPython\s*\d+\.\d+\+?", re.IGNORECASE),
    re.compile(r"\b(?:Apache|A?GPL|LGPL|MPL|CC-BY(?:-SA|-NC|-ND)*|ODC-BY|License)[- ]?v?\d+(?:\.\d+)*",
               re.IGNORECASE),
    re.compile(r"§\s*[\w.]+"),
]


def strip_identifiers(line: str) -> str:
    for rx in _IDENTIFIERS:
        line = rx.sub(" ", line)
    return line


def result_tokens(line: str) -> list[str]:
    """Result-like tokens in one line of prose, identifiers removed first."""
    return _NUM.findall(strip_identifiers(line))


def render_table(metrics: list[dict]) -> str:
    lines = [
        "# Results table",
        "",
        "Rendered from `results/registry.json` by `scripts/numbers_lock.py`; do not edit.",
        "",
        "| metric | value | 95% CI | n | split | source |",
        "|---|---|---|---|---|---|",
    ]
    for m in sorted(metrics, key=lambda x: x["metric_id"]):
        v = m["value"]
        val = "not measured" if v is None else f"{v}"
        ci = f"[{m['ci_lo']}, {m['ci_hi']}]" if m.get("ci_lo") is not None else ""
        n = "" if m.get("n") is None else str(m["n"])
        lines.append(f"| {m['metric_id']} | {val} | {ci} | {n} | {m['dev_or_heldout']} "
                     f"| {m['source']} |")
    if not metrics:
        lines.append("| (no results yet) | | | | | |")
    return "\n".join(lines) + "\n"


def allowed_strings(metrics: list[dict]) -> set[str]:
    allowed: set[str] = set()
    for m in metrics:
        vals = [m[k] for k in ("value", "ci_lo", "ci_hi") if m.get(k) is not None]
        for v in vals:
            fv = float(v)
            allowed.add(f"{v}")
            for d in (1, 2, 3, 4):
                allowed.add(f"{round(fv, d)}")
                allowed.add(f"{fv:.{d}f}")
            for d in (0, 1, 2):
                allowed.add(f"{round(fv * 100, d)}%")
                allowed.add(f"{fv * 100:.{d}f}%")
                allowed.add(f"{round(fv * 100, d)}")
                allowed.add(f"{fv * 100:.{d}f}")
    # a value registered in percent units (44.3) may be written 44.3% in the docs
    allowed |= {f"{a}%" for a in allowed if not a.endswith("%")}
    return allowed


def allowlist() -> set[str]:
    out: set[str] = set()
    for f in sorted(ALLOW_DIR.glob("*.txt")):
        for ln in f.read_text().splitlines():
            ln = ln.split("#", 1)[0].strip()
            if ln:
                out.add(ln)
    return out


def scanned_files() -> list[Path]:
    files = [REPO / f for f in SCAN_FILES]
    for g in SCAN_GLOBS:
        files += sorted(REPO.glob(g))
    seen, out = set(), []
    for f in files:
        if f.is_file() and f != TABLE and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def lock() -> int:
    REGISTRY.write_text(registry_text(RESULTS), encoding="utf-8")
    reg = json.loads(REGISTRY.read_text())
    sha = metrics_sha256(reg["metrics"])
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(render_table(reg["metrics"]), encoding="utf-8")
    rec = {"registry_metrics_sha256": sha, "n_metrics": len(reg["metrics"]),
           "components": sorted(reg["components"]),
           "note": "Docs render from this snapshot. A new snapshot requires re-checking "
                   "every doc that cited the previous one (make lock, then make ci)."}
    LOCK.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"numbers-lock: locked {len(reg['metrics'])} metrics, sha256 {sha[:16]}...")
    return 0


def check(strict: bool) -> int:
    ok = True
    committed = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else None
    if committed is None:
        print("numbers-lock: results/registry.json missing (run make lock).")
        return 1
    if LOCK.exists():
        locked = json.loads(LOCK.read_text())["registry_metrics_sha256"]
        if locked != metrics_sha256(committed["metrics"]):
            print("numbers-lock: registry changed since the lock (run make lock).")
            ok = False
    else:
        print("numbers-lock: results/NUMBERS_LOCK.json missing (run make lock).")
        ok = False
    if not TABLE.exists() or TABLE.read_text() != render_table(committed["metrics"]):
        print("numbers-lock: docs/tables/results.md is not a fresh render (run make lock).")
        ok = False
    merged = build_registry(RESULTS)
    if REGISTRY.read_text() != registry_text(RESULTS):
        msg = ("numbers-lock: results/registry.json differs from a fresh merge of "
               "results/<component>.json (the integrator runs make lock).")
        if strict:
            print(msg)
            ok = False
        else:
            print("warning: " + msg)
    allowed = allowed_strings(merged["metrics"]) | allowlist()
    offenders = []
    for f in scanned_files():
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for tok in result_tokens(line):
                if tok not in allowed:
                    offenders.append((f.relative_to(REPO).as_posix(), i, tok))
    if offenders:
        ok = False
        print("numbers-lock: result-like numbers not derivable from the registry "
              "(render them from results/, or allow-list a structural constant):")
        for rel, i, tok in offenders[:80]:
            print(f"  {rel}:{i}  {tok}")
    if ok:
        print(f"numbers-lock: OK ({len(merged['metrics'])} metrics; every result-like number "
              "in the docs renders from the registry).")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify instead of writing")
    ap.add_argument("--strict", action="store_true",
                    help="with --check: a stale registry.json is an error, not a warning")
    a = ap.parse_args(argv)
    return check(a.strict) if a.check else lock()


if __name__ == "__main__":
    raise SystemExit(main())
