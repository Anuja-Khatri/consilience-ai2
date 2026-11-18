"""Precision of W1 and W2 on a hand-labelled sample (rules v0.1 and v0.2), split ``dev``.

The pool: every unit flagged W1 or W2 under either rule version.

- SciArena: a citing sentence with at least one resolved citation (its claim against
  the concatenated passages of its resolved citations).
- Theorizer: an evidence item in a literature-supported condition (its text against the
  records it cites).

The sample. For each check (W1, W2), each dataset and each rule version, the 25 flagged
units with the smallest key ``sha256("precision-sample-v1:<check>:<item_id>")`` are
drawn. Ordering by a fixed hash is a uniform random sample without replacement for
each version, and because both versions use the same keys, a unit flagged under both
is drawn for both whenever it is drawn for either ("the same items where applicable").
So each version gets 50 units per check: 25 SciArena and 25 Theorizer.

The labels. Each sampled unit was read by one annotator (the author of the rules, so
neither blind nor independent) and labelled, separately for the tokens each version
flagged, ``true`` (the claim states a quantity, or a certainty, that the cited text does
not support) or ``false_alarm`` (it does: the number is there in another form, is not a
stated quantity, or the assertive word is not an epistemic upgrade), with a one-line
reason. The labels live in ``precision_sample.jsonl`` next to the short spans they
judge; a rerun reads them back by ``id`` and refuses to score an unlabelled unit.

Precision is the share of ``true`` labels, with a Wilson 95% interval. The two datasets
are weighted equally in the combined figure, not by how many flags each has.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from consilience_ai2.core.results import metric
from consilience_ai2.receipts.claims import certainty_profile
from consilience_ai2.receipts.numbers_w1 import extract_w1_numbers

HERE = Path(__file__).resolve().parent
OUT = HERE / "precision_sample.jsonl"
PER_STRATUM = 25
VERSIONS = ("v0.1", "v0.2")
DATASETS = ("sciarena", "theorizer")
SALT = "precision-sample-v1"
WINDOW = 60
SOURCES = {"sciarena": "fetch:sciarena-eval", "theorizer": "fetch:theorizer-paper-data"}
UNLABELLED_OK = "CONSILIENCE_RECEIPTS_ALLOW_UNLABELLED"


def key(check: str, item_id: str) -> str:
    return hashlib.sha256(f"{SALT}:{check}:{item_id}".encode()).hexdigest()


def _window(text: str, a: int, b: int, width: int = WINDOW) -> str:
    s, e = max(0, a - width), min(len(text), b + width)
    out = " ".join(text[s:e].split())
    return ("..." if s > 0 else "") + out + ("..." if e < len(text) else "")


def _first(text: str, needles: list[str], words: bool) -> tuple[int, int]:
    low = text.lower()
    best: tuple[int, int] | None = None
    for nd in needles:
        i = low.find(nd.lower())
        while i != -1 and words and (
                (i > 0 and low[i - 1].isalpha()) or
                (i + len(nd) < len(low) and low[i + len(nd)].isalpha())):
            i = low.find(nd.lower(), i + 1)
        if i != -1 and (best is None or i < best[0]):
            best = (i, i + len(nd))
    return best or (0, 0)


def flagged_tokens(check: str, flags: dict[str, Any]) -> list[str] | None:
    d = flags.get(check)
    if d is None:
        return None
    return list(d["unsupported"]) if check == "W1" else list(d["claim_assertive"])


def _unit_record(check: str, u: dict[str, Any], versions: list[str],
                 redact: Callable[[str], str]) -> dict[str, Any]:
    claim = u["claim"]
    f1 = flagged_tokens(check, u["flags"]["v0.1"])
    f2 = flagged_tokens(check, u["flags"]["v0.2"])
    toks = (f1 or []) + (f2 or [])
    a, b = _first(claim, toks, words=check == "W2")
    rec: dict[str, Any] = {
        "id": f"{check}:{u['item_id']}", "check": check, "dataset": u["dataset"],
        "drawn_for": versions,
        "flagged_v01": None if f1 is None else [redact(t) for t in f1],
        "flagged_v02": None if f2 is None else [redact(t) for t in f2],
        "claim_span": redact(_window(claim, a, b)),
    }
    parts = u["source_parts"]
    if check == "W1":
        nums: list[str] = []
        for p in parts:
            for n in extract_w1_numbers(p):
                if n.text not in nums:
                    nums.append(" ".join(n.text.split()))
        rec["source_numbers"] = [redact(x) for x in nums[:12]]
        rec["source_numbers_total"] = len(nums)
    else:
        hedges: list[str] = []
        for p in parts:
            hedges += list(certainty_profile(p, rules="v0.2").hedged)
        first = next((p for p in parts if certainty_profile(p, rules="v0.2").hedged), "")
        h = certainty_profile(first, rules="v0.2").hedged[:1] if first else ()
        fa, fb = _first(first, list(h), words=True) if h else (0, 0)
        rec["source_hedged"] = sorted(set(hedges))[:8]
        rec["source_span"] = redact(_window(first, fa, fb, 50)) if first else ""
    rec["receipt"] = u["receipt"]
    return rec


def draw(pool: list[dict[str, Any]],
         redact: Callable[[str], str] = lambda x: x) -> list[dict[str, Any]]:
    """The sample, before labels: one record per (check, unit), sorted by id. ``redact``
    replaces model identifiers in the short spans (the repository holds none)."""
    chosen: dict[str, tuple[dict[str, Any], dict[str, list[str]]]] = {}
    for check in ("W1", "W2"):
        for ds in DATASETS:
            for ver in VERSIONS:
                cand = [u for u in pool if u["dataset"] == ds and check in u["flags"][ver]]
                cand.sort(key=lambda u: key(check, u["item_id"]))
                for u in cand[:PER_STRATUM]:
                    rid = f"{check}:{u['item_id']}"
                    chosen.setdefault(rid, (u, {"check": [check], "versions": []}))[1][
                        "versions"].append(ver)
    out = []
    for rid in sorted(chosen):
        u, meta = chosen[rid]
        out.append(_unit_record(meta["check"][0], u, meta["versions"], redact))
    return out


LABEL_FIELDS = ("label_v01", "reason_v01", "label_v02", "reason_v02")


def attach_labels(sample: list[dict[str, Any]], path: Path = OUT) -> list[dict[str, Any]]:
    """Copy the labels already written in ``path`` onto the freshly drawn sample, by id."""
    old: dict[str, dict[str, Any]] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                old[r["id"]] = r
    for r in sample:
        prev = old.get(r["id"], {})
        same = (prev.get("flagged_v01") == r["flagged_v01"]
                and prev.get("flagged_v02") == r["flagged_v02"])
        for f in LABEL_FIELDS:
            r[f] = prev.get(f) if same else None
    return sample


def write(sample: list[dict[str, Any]], path: Path = OUT) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                            for r in sample), encoding="utf-8")


def _wilson(k: int, n: int) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    from scipy.stats import binomtest
    ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    return round(float(ci.low), 6), round(float(ci.high), 6)


def metrics(sample: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing = []
    for r in sample:
        for ver, lf in (("v0.1", "label_v01"), ("v0.2", "label_v02")):
            if ver in r["drawn_for"] and r.get(lf) not in ("true", "false_alarm"):
                missing.append(f"{r['id']} ({ver})")
    if missing:
        if os.environ.get(UNLABELLED_OK):
            return []
        raise SystemExit(f"{len(missing)} sampled units have no label in {OUT}, e.g. "
                         f"{missing[:3]}; label them before scoring")
    out: list[dict[str, Any]] = []
    cav = ["dev: one annotator (the author of the rules), not blind, not independent",
           "labels and short spans in analyses/receipts/precision_sample.jsonl",
           f"{PER_STRATUM} SciArena citing sentences and {PER_STRATUM} Theorizer evidence "
           "items per version, drawn by a fixed hash (see precision_sample.py); the two "
           "datasets are weighted equally, not by their number of flags"]
    test = "Wilson 95% interval on the labelled sample"
    for check in ("W1", "W2"):
        for ver, lf, tag in (("v0.1", "label_v01", "v01"), ("v0.2", "label_v02", "v02")):
            rows = [r for r in sample if r["check"] == check and ver in r["drawn_for"]]
            for ds, sel in (("all", rows),
                            *((d, [r for r in rows if r["dataset"] == d]) for d in DATASETS)):
                k = sum(r[lf] == "true" for r in sel)
                n = len(sel)
                lo, hi = _wilson(k, n)
                suffix = "" if ds == "all" else f"_{ds}"
                out.append(metric(
                    f"receipts.precision.{check.lower()}_{tag}{suffix}",
                    round(k / n, 6) if n else None, n=n, ci_lo=lo, ci_hi=hi,
                    source=SOURCES[ds] if ds != "all" else "fetch:sciarena-eval+theorizer-paper-data",
                    dev_or_heldout="dev", caveats=cav + [f"W1/W2 rules {ver}"],
                    unit="proportion", test=test,
                    description=f"precision of {check} (rules {ver}): flagged units labelled "
                                "a true overreach" + ("" if ds == "all" else f", {ds} only")))
    return out


def run(pool: list[dict[str, Any]], redact: Callable[[str], str] = lambda x: x,
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sample = attach_labels(draw(pool, redact))
    write(sample)
    summary: dict[str, Any] = {"units_labelled": len(sample)}
    for check in ("W1", "W2"):
        rows = [r for r in sample if r["check"] == check]
        both = [r for r in rows if set(r["drawn_for"]) == set(VERSIONS)]
        summary[check] = {
            "units": len(rows), "drawn_for_both_versions": len(both),
            "v01_flags_dropped_by_v02": sum(
                1 for r in rows if "v0.1" in r["drawn_for"] and r["flagged_v02"] is None),
            "v01_false_alarms_dropped_by_v02": sum(
                1 for r in rows if "v0.1" in r["drawn_for"] and r["flagged_v02"] is None
                and r.get("label_v01") == "false_alarm"),
            "v01_true_flags_dropped_by_v02": sum(
                1 for r in rows if "v0.1" in r["drawn_for"] and r["flagged_v02"] is None
                and r.get("label_v01") == "true"),
            "v02_flags_new_in_v02": sum(
                1 for r in rows if "v0.2" in r["drawn_for"] and r["flagged_v01"] is None),
            "v02_true_flags_new_in_v02": sum(
                1 for r in rows if "v0.2" in r["drawn_for"] and r["flagged_v01"] is None
                and r.get("label_v02") == "true"),
        }
    return metrics(sample), summary
