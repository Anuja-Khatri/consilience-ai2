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

v0.2 extraction (rule fixed in ``prereg/reproduce/cs_extraction_v0_2.md``; parsers in
``cs_extract.py``). The pairs, the thresholds, the record and the verdict code are the
same as v0.1; only how a run's numbers are found changes:
- tiers in the final iteration: ``results.json`` (v0.1), then ``to_save/**/*.json``, then
  bootstrap blocks printed in ``log.json``; tolerant parsing (encodings, NaN tokens,
  Python literals, trailing commas);
- several candidates: the comparison named in the run's hypothesis, else in its
  experiment plan (``data/all-experiments.json``), by token matching; still tied, the
  pair stays ``no_data`` and every comparison found in both runs is reported separately
  (``per_comparison``), never counted as a pair;
- runs with no bootstrap block anywhere are classified: other test output (complete or
  not) or no test output at all.
v0.1 numbers are still computed and written; v0.2 metrics sit beside them.

Second batch: the batch WITHOUT expert notes has bulk and meta-analysis tables in the
repository but no run outputs: ``batch2_search`` looks for its run directories in the
full-50 zip, the example-experiments zip (when fetched) and the repository, and counts
what it finds.
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

import cs_extract as cx  # sibling module: the script directory is on sys.path
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


def _final_files(z: zipfile.ZipFile, members: list[str]) -> tuple[str | None, dict[str, bytes]]:
    """The final iteration's outputs read by the v0.2 tiers: results.json,
    to_save/**/*.json and log.json, keyed by their path inside modal-output/."""
    finals = sorted(m for m in members if m.endswith("modal-output/results.json"))
    if not finals:
        return None, {}
    base = finals[-1][: -len("results.json")]
    files: dict[str, bytes] = {}
    for m in sorted(members):
        if not m.startswith(base) or m.endswith("/"):
            continue
        rel = m[len(base):]
        if rel in ("results.json", "log.json") or (rel.startswith("to_save/")
                                                   and rel.endswith(".json")):
            files[rel] = z.read(m)
    return finals[-1], files


def numbers_from_block(blk: cx.Block, pilot_mode: Any) -> dict[str, Any]:
    """Record fields from one bootstrap block (the same reading as v0.1)."""
    b = blk.raw
    me, mb, p, n = (_number(b["mean_experimental"]), _number(b["mean_baseline"]),
                    _number(b["p_value"]), b["dataset_size"])
    if me is None or mb is None or p is None or not isinstance(n, int) or isinstance(n, bool) \
            or n < 1 or not 0 <= p <= 1:
        return {"status": "unreadable_numbers"}
    meas: dict[str, Any] = {"quantity": f"bootstrap comparison at {blk.where}: mean "
                                        "experimental minus mean baseline",
                            "value": me - mb, "unit": "dimensionless", "n": n, "p": p}
    dz = dz_from_p(p, n, b.get("num_resamples"))
    if dz is not None:
        meas["effect_size"] = {"type": "dz", "value": dz}
    return {"status": "ok", "path": blk.where, "measurement": meas, "pilot_mode": pilot_mode}


def run_numbers_v02(z: zipfile.ZipFile, members: list[str], hypothesis: str,
                    plan: str) -> dict[str, Any]:
    """v0.2: the tiers and the primary-comparison rule of ``cs_extract``."""
    final, files = _final_files(z, members)
    if final is None:
        return {"status": "no_results_file"}
    ex = cx.extract_run(files, hypothesis, plan)
    info = {"tier": ex.tier, "basis": ex.basis, "parse": ex.parse,
            "candidates": ex.candidates, "other_tests": ex.other_tests,
            "other_tests_complete": ex.other_tests_complete,
            "results_pilot_mode": _pilot_mode(ex.results_obj)}
    if ex.status != "ok":
        return {"status": ex.status, **info}
    pm = _pilot_mode(ex.results_obj)
    if pm is None and ex.source_obj is not ex.results_obj:
        pm = _pilot_mode(ex.source_obj)
    out = numbers_from_block(ex.primary, pm)
    if out["status"] != "ok":
        return {**out, **info}
    out.update(info, final=final, label=ex.primary.label)
    if len(ex.controls) == 1:
        cp = _number(ex.controls[0].raw["p_value"])
        if cp is not None:
            out["control_p"] = cp
    return out


def build_record(idea: str, src: dict, rep: dict, key: str = "numbers") -> dict[str, Any]:
    """A reproduction record for one (source run, reproduction run) pair, from the run
    numbers under ``key`` (``numbers``: v0.1; ``numbers_v02``: v0.2)."""
    rec: dict[str, Any] = {
        "schema_version": 1,
        "id": f"{idea}:{src['name']}->{rep['name']}",
        "hypothesis": rep["hypothesis"],
        "source_hypothesis": src["hypothesis"],
        "direction": "positive",
        "thresholds": dict(THRESHOLDS),
        "independence_axis": "time",
    }
    sn, rn = src[key], rep[key]
    ok_src = sn["status"] == "ok"
    ok_rep = rn["status"] == "ok"
    if not (ok_src and ok_rep):
        # Not recoverable: D1 no_data. Nothing else of the pair is compared.
        generic = "the run's primary bootstrap comparison"
        why = sn["status"] if not ok_src else rn["status"]
        side = "source" if not ok_src else "reproduction"
        rec.pop("independence_axis")
        rec["source"] = {"quantity": generic}
        rec["reproduction"] = {"quantity": generic, "status": "no_data",
                               "note": f"{side} numbers not recoverable: {why}"}
        rec["quantity_mapping"] = {"relation": "same_quantity"}
        return rec
    for side, run, num in (("source", src, sn), ("reproduction", rep, rn)):
        m = dict(num["measurement"])
        m["conditions"] = {"time": run["ts"]}
        if num["pilot_mode"] is not None:
            m["conditions"]["pilot_mode"] = num["pilot_mode"]
        rec[side] = m
    same = sn["path"] == rn["path"]
    single = all(x.get("basis", "single") == "single" for x in (sn, rn))
    rec["quantity_mapping"] = {"relation": "same_quantity"} if same else {
        "relation": "proxy",
        "note": "role-matched: each run's single non-random bootstrap comparison" if single
        else "role-matched: each run's primary bootstrap comparison (v0.2 rule)"}
    if rn.get("control_p") is not None:
        rec["positive_control"] = {"p": rn["control_p"]}
    return rec


def _files() -> tuple[Path, Path, Path]:
    repo = require("codescientist")
    meta = sorted((repo / "metaanalysis").glob("*withexpertnotes*meta-analysis.json"))
    bulk = sorted((repo / "metaanalysis").glob("*withexpertnotes*bulk.tsv"))
    if len(meta) != 1 or len(bulk) != 1:
        raise RuntimeError("expected one with-expert-notes meta-analysis and bulk file")
    return meta[0], bulk[0], require("codescientist-full50")


def _plans(repo: Path, batch_marker: str) -> dict[str, str]:
    """Experiment plan per run directory name (``experiment_description`` in
    ``data/all-experiments.json``, matched by ``experiment_path``)."""
    exps = json.loads((repo / "data" / "all-experiments.json").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for e in exps["experiment_list"]:
        if batch_marker not in (e.get("batch_name") or ""):
            continue
        path = (e.get("experiment_path") or "").rstrip("/")
        if path:
            out[path.split("/")[-1]] = e.get("experiment_description") or ""
    return out


def batch2_search(full50: zipfile.ZipFile) -> dict[str, Any]:
    """Where the batch without expert notes could have run outputs, and what is there."""
    repo = require("codescientist")
    bulk = sorted((repo / "metaanalysis").glob("*noexpertnotes*bulk.tsv"))
    if len(bulk) != 1:
        raise RuntimeError("expected one without-expert-notes bulk file")
    with bulk[0].open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    completed: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        cm = _COPY.search(r["experiment_name"])
        if r["status"] == "completed" and cm:
            completed[r["experiment_name"][: cm.start()]].append(int(cm.group(1)))
    exps = json.loads((repo / "data" / "all-experiments.json").read_text(encoding="utf-8"))
    dirs = {(e.get("experiment_path") or "").rstrip("/").split("/")[-1]
            for e in exps["experiment_list"]
            if "noexpertnotes" in (e.get("batch_name") or "") and e.get("experiment_path")}
    examples = zipfile.ZipFile(require("codescientist-example-experiments"))
    found = {"full50_zip": 0, "example_experiments_zip": 0, "codescientist_repository": 0}
    for key, names in (("full50_zip", full50.namelist()),
                       ("example_experiments_zip", examples.namelist())):
        seen = {seg for n in names for seg in n.split("/")[:3]}
        found[key] = len(dirs & seen)
    repo_dirs = {p.name for p in repo.rglob("*") if p.is_dir() and ".git" not in p.parts}
    found["codescientist_repository"] = len(dirs & repo_dirs)
    return {"completed_runs": sum(len(v) for v in completed.values()),
            "ideas_2plus": sum(1 for v in completed.values() if len(v) >= 2),
            "pairs": sum(len(v) - 1 for v in completed.values() if len(v) >= 2),
            "run_directories_named": len(dirs), "run_directories_found": found}


def _comparison_pairs(idea: str, src: dict, rep: dict) -> list[dict[str, Any]]:
    """Per-comparison records for a pair with an ambiguous side: every comparison whose
    words match exactly one candidate in each run (the same comparison in both)."""
    def cands(run: dict) -> list[cx.Block]:
        n = run["numbers_v02"]
        return list(n.get("candidates") or [])
    sc, rc = cands(src), cands(rep)
    if src["numbers_v02"]["status"] == "ok":
        sc = [c for c in sc if c.where == src["numbers_v02"]["path"]]
    if rep["numbers_v02"]["status"] == "ok":
        rc = [c for c in rc if c.where == rep["numbers_v02"]["path"]]
    sk = Counter(cx.comparison_key(c.label) for c in sc)
    rk = Counter(cx.comparison_key(c.label) for c in rc)
    out = []
    for key in sorted(k for k in sk if sk[k] == 1 and rk.get(k) == 1 and k):
        a = next(c for c in sc if cx.comparison_key(c.label) == key)
        b = next(c for c in rc if cx.comparison_key(c.label) == key)
        na = numbers_from_block(a, src["numbers_v02_pilot"])
        nb = numbers_from_block(b, rep["numbers_v02_pilot"])
        s2 = {**src, "cmp": na}
        r2 = {**rep, "cmp": nb}
        rec = build_record(idea, s2, r2, key="cmp")
        rec["id"] += ":" + " ".join(key)
        v = evaluate(rec, backend="fallback", skip=("P1",)).extra["verdict"]
        out.append({"idea": idea, "source": src["name"], "reproduction": rep["name"],
                    "comparison": " ".join(key), **v})
    return out


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
    plans = _plans(require("codescientist"), "withexpertnotes")

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
        run["numbers_v02"] = (run_numbers_v02(z, members[d[0]], row["hypothesis"],
                                              plans.get(d[0], ""))
                              if d else {"status": "no_run_directory"})
        run["numbers_v02_pilot"] = (run["numbers_v02"]["pilot_mode"]
                                    if run["numbers_v02"]["status"] == "ok"
                                    else run["numbers_v02"].get("results_pilot_mode"))
        ideas[idea].append(run)

    pairs: list[dict[str, Any]] = []
    pairs_v02: list[dict[str, Any]] = []
    per_comparison: list[dict[str, Any]] = []
    for idea in sorted(ideas):
        runs = sorted(ideas[idea], key=lambda r: r["copy"])
        if len(runs) < 2:
            continue
        for rep in runs[1:]:
            common = {"idea": idea, "source": runs[0]["name"], "reproduction": rep["name"],
                      "theirs": judgement.get(_key(rep["name"])),
                      "theirs_source": judgement.get(_key(runs[0]["name"])),
                      "category": category.get(_key(idea))}
            for key, out in (("numbers", pairs), ("numbers_v02", pairs_v02)):
                rec = build_record(idea, runs[0], rep, key=key)
                v = evaluate(rec, backend="fallback", skip=("P1",)).extra["verdict"]
                extra = {}
                if key == "numbers_v02":
                    extra = {"source_tier": runs[0][key].get("tier"),
                             "reproduction_tier": rep[key].get("tier"),
                             "source_basis": runs[0][key].get("basis"),
                             "reproduction_basis": rep[key].get("basis")}
                out.append({**common, "source_status": runs[0][key]["status"],
                            "reproduction_status": rep[key]["status"], **extra, **v})
            st = {runs[0]["numbers_v02"]["status"], rep["numbers_v02"]["status"]}
            if "ambiguous_primary" in st and st <= {"ok", "ambiguous_primary"}:
                per_comparison.extend(_comparison_pairs(idea, runs[0], rep))
    run_status = Counter(r["numbers_v02"]["status"] for rs in ideas.values() for r in rs)
    run_tier = Counter(f'{r["numbers_v02"].get("tier")}|{r["numbers_v02"].get("basis")}'
                       for rs in ideas.values() for r in rs if r["numbers_v02"]["status"] == "ok")
    repaired = sum(1 for rs in ideas.values() for r in rs
                   for h in (r["numbers_v02"].get("parse") or {}).values() if h == "repaired")
    return {"pairs": pairs, "pairs_v02": pairs_v02, "per_comparison": per_comparison,
            "runs_v02": {"status": dict(run_status), "tier_basis": dict(run_tier),
                         "files_repaired": repaired,
                         "n_runs": sum(len(v) for v in ideas.values())},
            "batch2": batch2_search(z),
            "n_ideas_completed": len(ideas),
            "n_ideas_2plus": len({p["idea"] for p in pairs}),
            "n_ideas_meta": len(meta)}


THEIRS_TO_OURS = {"support": "reproduced", "refute": "not_reproduced",
                  "inconclusive": "inconclusive"}


def summarise(res: dict[str, Any], pairs_key: str = "pairs") -> dict[str, Any]:
    """Counts over the pairs (v0.1: ``pairs``; v0.2: ``pairs_v02``)."""
    pairs = res[pairs_key]
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


def summarise_v02(res: dict[str, Any]) -> dict[str, Any]:
    """v0.2 counts: the pair summary, the change from v0.1, run-level extraction, the
    per-comparison report and the second-batch search."""
    s = summarise(res, "pairs_v02")
    old = {(p["source"], p["reproduction"]): p for p in res["pairs"]}
    trans = Counter(f'{old[(p["source"], p["reproduction"])]["verdict"]}|{p["verdict"]}'
                    for p in res["pairs_v02"])
    newly = [p for p in res["pairs_v02"] if p["source_status"] == "ok"
             and p["reproduction_status"] == "ok"
             and not (old[(p["source"], p["reproduction"])]["source_status"] == "ok"
                      and old[(p["source"], p["reproduction"])]["reproduction_status"] == "ok")]
    how = Counter("|".join(sorted({f'{p["source_tier"]}:{p["source_basis"]}',
                                   f'{p["reproduction_tier"]}:{p["reproduction_basis"]}'}))
                  for p in newly)
    pc = res["per_comparison"]
    s.update({"verdict_transitions": dict(trans), "n_newly_recoverable": len(newly),
              "newly_recoverable_how": dict(how),
              "runs": res["runs_v02"],
              "per_comparison": {"n": len(pc),
                                 "n_pairs": len({(p["source"], p["reproduction"]) for p in pc}),
                                 "verdict": dict(Counter(p["verdict"] for p in pc)),
                                 "outcome": dict(Counter(p["outcome_label"] for p in pc))},
              "batch2": res["batch2"]})
    return s


if __name__ == "__main__":
    r = analyse()
    print(json.dumps({"v0.1": summarise(r), "v0.2": summarise_v02(r)}, indent=2,
                     sort_keys=True))
