"""(a) CodeScientist reruns read as reproductions. Label: descriptive.

Data (no network; ``consilience-ai2 fetch codescientist codescientist-full50``):
- ``codescientist`` (git): the meta-analysis of the full-50 batch WITH expert notes
  (``metaanalysis/*withexpertnotes*meta-analysis.json`` and ``*bulk.tsv``). This is the
  batch whose run outputs are released; the batch without expert notes has no released
  run outputs, so it is not used.
- ``codescientist-full50`` (zip, read in place): each run's directory with every
  debugging iteration ``modal-python-<timestamp>/modal-output/results.json``.

Design (fixed before reading any verdict):
- An idea's completed runs (``status == completed`` in the bulk TSV) are ordered by their
  copy number. Ideas with at least 2 are used: the first is the source, every later one
  a reproduction (one record per pair).
- A run's numbers come from its FINAL results file: the last iteration (by timestamp)
  that wrote ``results.json``. The numbers are those of CodeScientist's own bootstrap
  routine, recognised by its output signature (``mean_baseline``, ``mean_experimental``,
  ``p_value``, ``dataset_size``). Comparisons against a random agent (a path segment
  containing "random") are positive controls; the run's PRIMARY comparison is its single
  other bootstrap block. No block, an unreadable file, or more than one candidate means
  the numbers are not recoverable: the pair is recorded with ``status: no_data`` (D1
  ``no_data``), and the reason is counted in the coverage metrics. A source run that is
  not recoverable makes every pair of its idea ``no_data``.
- Value: ``mean_experimental - mean_baseline`` (dimensionless); n: ``dataset_size``; p:
  ``p_value`` (one-sided: the share of resamples where the experimental mean is not
  above the baseline). Effect size ``dz`` = ``Phi^-1(1 - p) / sqrt(n)``, the normal
  approximation of the paired bootstrap, with p clipped to ``[1/R, 1 - 1/R]`` for R
  resamples (unidentified when p is 0 or 1 and R is not given).
- Quantity: the primary block's key path. Same path in both runs: ``same_quantity``.
  Different paths: declared ``proxy`` (role-matched: each run's single non-random
  comparison), carried as a caveat.
- Conditions: ``pilot_mode`` (top level, or one level down) when present; independence
  axis ``time`` (the run's start time). A condition stated in one run only is
  ``not_comparable`` (fail closed).
- Thresholds (committed in this file): alpha 0.05, one-sided (the bootstrap's own
  test), direction positive (experimental above baseline), minimum effect 0 on the value
  scale, power threshold 0.8. Positive control: the run's random-agent comparison, when
  there is exactly one, passes at p < alpha.
- Hypothesis texts (P2): the reproduction run's stated hypothesis against the source
  run's (bulk TSV), compared after ``core.normalise``.
- P1 is skipped: these records are built in memory, not committed.
- F1 uses the fallback backend so the numbers do not depend on whether ``consilience``
  is installed (the conditions here are plain text, where both backends agree).

Agreement with CodeScientist's own labels: its meta-analysis gives a judgement per run
(support / refute / inconclusive) and a consistency category per idea. Per pair, the
reproduction run's judgement is set beside our V1 verdict (reproduced ~ support,
not_reproduced ~ refute, inconclusive ~ inconclusive).
"""

from __future__ import annotations

import csv
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import norm

from consilience_ai2.fetch import require
from consilience_ai2.reproduce import evaluate

SIG = ("mean_baseline", "mean_experimental", "p_value", "dataset_size")
THRESHOLDS = {"alpha": 0.05, "sides": 1, "minimum_effect": 0, "minimum_effect_scale": "value",
              "power": 0.8}
_DIR = re.compile(r"^(?P<key>.*)-(?P<ts>\d{8}-\d{6})$")
_COPY = re.compile(r"-copy(\d+)$")


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _blocks(obj: Any, path: tuple[str, ...] = ()):
    if isinstance(obj, dict):
        if all(k in obj for k in SIG):
            yield ".".join(path), obj
        for k in sorted(obj, key=str):
            yield from _blocks(obj[k], path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _blocks(v, path + (f"[{i}]",))


def _pilot_mode(obj: Any) -> Any:
    if not isinstance(obj, dict):
        return None
    if "pilot_mode" in obj:
        return obj["pilot_mode"]
    for k in sorted(obj, key=str):
        v = obj[k]
        if isinstance(v, dict) and "pilot_mode" in v:
            return v["pilot_mode"]
    return None


def _is_random(path: str) -> bool:
    return any("random" in seg.casefold() for seg in path.split("."))


def _number(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, int | float):
        return None
    return float(v) if math.isfinite(v) else None


def dz_from_p(p: float, n: int, resamples: Any) -> float | None:
    """The paired standardised effect implied by a one-sided bootstrap p (see above)."""
    r = _number(resamples)
    if p <= 0 or p >= 1:
        if r is None or r < 2:
            return None
        p = min(max(p, 1 / r), 1 - 1 / r)
    return float(norm.ppf(1 - p)) / math.sqrt(n)


def run_numbers(z: zipfile.ZipFile, members: list[str]) -> dict[str, Any]:
    """The final results file of one run, read into record fields (or a no_data reason)."""
    finals = sorted(m for m in members if m.endswith("modal-output/results.json"))
    if not finals:
        return {"status": "no_results_file"}
    final = finals[-1]
    try:
        obj = json.loads(z.read(final))
    except (ValueError, UnicodeDecodeError):
        return {"status": "unreadable_results_file"}
    blocks = list(_blocks(obj))
    primary = [(p, b) for p, b in blocks if not _is_random(p)]
    control = [(p, b) for p, b in blocks if _is_random(p)]
    if not primary:
        return {"status": "no_bootstrap_block"}
    if len(primary) > 1:
        return {"status": "ambiguous_primary"}
    path, b = primary[0]
    me, mb, p, n = (_number(b["mean_experimental"]), _number(b["mean_baseline"]),
                    _number(b["p_value"]), b["dataset_size"])
    if me is None or mb is None or p is None or not isinstance(n, int) or isinstance(n, bool) \
            or n < 1 or not 0 <= p <= 1:
        return {"status": "unreadable_numbers"}
    meas: dict[str, Any] = {"quantity": f"bootstrap comparison at {path}: mean experimental "
                                        "minus mean baseline",
                            "value": me - mb, "unit": "dimensionless", "n": n, "p": p}
    dz = dz_from_p(p, n, b.get("num_resamples"))
    if dz is not None:
        meas["effect_size"] = {"type": "dz", "value": dz}
    pm = _pilot_mode(obj)
    out: dict[str, Any] = {"status": "ok", "path": path, "measurement": meas,
                           "pilot_mode": pm, "final": final}
    if len(control) == 1:
        cp = _number(control[0][1]["p_value"])
        if cp is not None:
            out["control_p"] = cp
    return out


def build_record(idea: str, src: dict, rep: dict) -> dict[str, Any]:
    """A reproduction record for one (source run, reproduction run) pair."""
    rec: dict[str, Any] = {
        "schema_version": 1,
        "id": f"{idea}:{src['name']}->{rep['name']}",
        "hypothesis": rep["hypothesis"],
        "source_hypothesis": src["hypothesis"],
        "direction": "positive",
        "thresholds": dict(THRESHOLDS),
        "independence_axis": "time",
    }
    ok_src = src["numbers"]["status"] == "ok"
    ok_rep = rep["numbers"]["status"] == "ok"
    if not (ok_src and ok_rep):
        # Not recoverable: D1 no_data. Nothing else of the pair is compared.
        generic = "the run's primary bootstrap comparison"
        why = src["numbers"]["status"] if not ok_src else rep["numbers"]["status"]
        side = "source" if not ok_src else "reproduction"
        rec.pop("independence_axis")
        rec["source"] = {"quantity": generic}
        rec["reproduction"] = {"quantity": generic, "status": "no_data",
                               "note": f"{side} numbers not recoverable: {why}"}
        rec["quantity_mapping"] = {"relation": "same_quantity"}
        return rec
    for key, run in (("source", src), ("reproduction", rep)):
        m = dict(run["numbers"]["measurement"])
        m["conditions"] = {"time": run["ts"]}
        if run["numbers"]["pilot_mode"] is not None:
            m["conditions"]["pilot_mode"] = run["numbers"]["pilot_mode"]
        rec[key] = m
    same = src["numbers"]["path"] == rep["numbers"]["path"]
    rec["quantity_mapping"] = {"relation": "same_quantity"} if same else {
        "relation": "proxy",
        "note": "role-matched: each run's single non-random bootstrap comparison"}
    if rep["numbers"].get("control_p") is not None:
        rec["positive_control"] = {"p": rep["numbers"]["control_p"]}
    return rec


def _files() -> tuple[Path, Path, Path]:
    repo = require("codescientist")
    meta = sorted((repo / "metaanalysis").glob("*withexpertnotes*meta-analysis.json"))
    bulk = sorted((repo / "metaanalysis").glob("*withexpertnotes*bulk.tsv"))
    if len(meta) != 1 or len(bulk) != 1:
        raise RuntimeError("expected one with-expert-notes meta-analysis and bulk file")
    return meta[0], bulk[0], require("codescientist-full50")


def analyse() -> dict[str, Any]:
    meta_path, bulk_path, zip_path = _files()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    judgement: dict[str, str] = {}
    category: dict[str, str] = {}
    for idea in meta:
        ma = idea["meta-analysis"]
        category[_key(idea["idea"]["research_idea_name"])] = ma["categorization"]
        for j in ma["support_refute_inconclusive_judgements"]:
            judgement[_key(j["specific_experiment_name"])] = j["judgement"]
    with bulk_path.open(encoding="utf-8", newline="") as f:
        bulk = list(csv.DictReader(f, delimiter="\t"))

    z = zipfile.ZipFile(zip_path)
    members: dict[str, list[str]] = defaultdict(list)
    dirs: dict[str, tuple[str, str]] = {}
    for name in z.namelist():
        parts = name.split("/")
        if len(parts) < 3:
            continue
        m = _DIR.match(parts[1])
        if m:
            members[parts[1]].append(name)
            dirs.setdefault(m.group("key"), (parts[1], m.group("ts")))

    ideas: dict[str, list[dict]] = defaultdict(list)
    for row in bulk:
        if row["status"] != "completed":
            continue
        cm = _COPY.search(row["experiment_name"])
        if not cm:
            continue  # follow-on runs are not among the five reruns
        idea = row["experiment_name"][: cm.start()]
        d = dirs.get(_key(row["experiment_name"]))
        run = {"name": row["experiment_name"], "copy": int(cm.group(1)),
               "hypothesis": row["hypothesis"], "ts": d[1] if d else None}
        run["numbers"] = run_numbers(z, members[d[0]]) if d else {"status": "no_run_directory"}
        ideas[idea].append(run)

    pairs: list[dict[str, Any]] = []
    for idea in sorted(ideas):
        runs = sorted(ideas[idea], key=lambda r: r["copy"])
        if len(runs) < 2:
            continue
        for rep in runs[1:]:
            rec = build_record(idea, runs[0], rep)
            report = evaluate(rec, backend="fallback", skip=("P1",))
            v = report.extra["verdict"]
            pairs.append({"idea": idea, "source": runs[0]["name"], "reproduction": rep["name"],
                          "source_status": runs[0]["numbers"]["status"],
                          "reproduction_status": rep["numbers"]["status"],
                          "theirs": judgement.get(_key(rep["name"])),
                          "theirs_source": judgement.get(_key(runs[0]["name"])),
                          "category": category.get(_key(idea)), **v})
    return {"pairs": pairs, "n_ideas_completed": len(ideas),
            "n_ideas_2plus": len({p["idea"] for p in pairs}),
            "n_ideas_meta": len(meta)}


THEIRS_TO_OURS = {"support": "reproduced", "refute": "not_reproduced",
                  "inconclusive": "inconclusive"}


def summarise(res: dict[str, Any]) -> dict[str, Any]:
    pairs = res["pairs"]
    cov = Counter("recoverable" if p["source_status"] == "ok" and p["reproduction_status"] == "ok"
                  else (p["source_status"] if p["source_status"] != "ok"
                        else p["reproduction_status"]) for p in pairs)
    recoverable = [p for p in pairs if p["source_status"] == "ok" and
                   p["reproduction_status"] == "ok"]
    f1 = Counter(p["faithfulness"].split("(")[0] for p in recoverable)
    f1_targets = Counter(p["faithfulness"] for p in recoverable
                         if p["faithfulness"].startswith("not_comparable"))
    d1 = Counter(p["decidability"] for p in pairs)
    v1 = Counter(p["verdict"] for p in pairs)
    outcome = Counter(p["outcome_label"] for p in pairs)
    p2 = Counter(p["hypothesis_copy"] for p in pairs)
    labelled = [p for p in pairs if p["theirs"] in THEIRS_TO_OURS]
    cross = Counter((p["verdict"], p["theirs"]) for p in labelled)
    agree = sum(THEIRS_TO_OURS[p["theirs"]] == p["verdict"] for p in labelled)
    # Their run-level consistency for the pair: both runs judged, same judgement or not.
    both = [p for p in pairs if p["theirs"] in THEIRS_TO_OURS and
            p["theirs_source"] in THEIRS_TO_OURS]
    consistent = Counter(("same" if p["theirs"] == p["theirs_source"] else "different",
                          p["verdict"]) for p in both)
    return {"n_pairs": len(pairs), "coverage": dict(cov), "f1": dict(f1),
            "n_recoverable": len(recoverable), "f1_not_comparable": dict(f1_targets),
            "d1": dict(d1),
            "v1": dict(v1), "outcome": dict(outcome), "p2": dict(p2),
            "n_labelled": len(labelled), "agree": agree,
            "cross": {f"{a}|{b}": c for (a, b), c in sorted(cross.items())},
            "n_both_judged": len(both),
            "consistency_cross": {f"{a}|{b}": c for (a, b), c in sorted(consistent.items())},
            "categories": dict(Counter(p["category"] for p in pairs)),
            "n_ideas_2plus": res["n_ideas_2plus"], "n_ideas_meta": res["n_ideas_meta"],
            "n_ideas_completed": res["n_ideas_completed"]}


if __name__ == "__main__":
    print(json.dumps(summarise(analyse()), indent=2, sort_keys=True))
