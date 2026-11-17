"""Shared loaders for the CodeScientist analyses (dev and held-out).

Data comes only through ``consilience_ai2.fetch.require``; zip archives are read in
place, member by member, never extracted.
"""

from __future__ import annotations

import csv
import json
import re
import zipfile
from functools import lru_cache
from pathlib import Path

from consilience_ai2.audit import Tree
from consilience_ai2.audit.adapters import load_codescientist_experiment
from consilience_ai2.audit.engine import audit
from consilience_ai2.audit.model import Run
from consilience_ai2.fetch import require

# The two full50 meta-analysis files in the codescientist repository. The full50 zip is
# the with-expert-notes batch (its top folder says so), so that batch's files are used.
META_GLOB = "*withexpertnotes*meta-analysis.json"
REVIEWS = "reviews/codescientist_external_review_ratings.tsv"
EXAMPLES_PREFIX = "example-experiments/"

_DIR_RX = re.compile(r"^(?P<idea>[a-z]+?)copy(?P<copy>\d+)(?P<follow>followon\w*)?-\d{8}-\d{6}$")


def idea_of_dir(dirname: str) -> str:
    """``simpleplanningagentcopy3-20250204-151159`` -> ``simpleplanningagent``."""
    m = _DIR_RX.match(dirname)
    if not m:
        raise ValueError(f"not a CodeScientist experiment directory name: {dirname}")
    return m.group("idea")


def run_key_of_dir(dirname: str) -> str:
    """``simpleplanningagentcopy3-20250204-151159`` -> ``simpleplanningagentcopy3``
    (the meta-analysis names it ``simple-planning-agent-copy3``)."""
    m = _DIR_RX.match(dirname)
    if not m:
        raise ValueError(dirname)
    return f"{m.group('idea')}copy{m.group('copy')}" + (m.group("follow") or "")


def key_of_experiment_name(name: str) -> str:
    return name.replace("-", "").lower()


@lru_cache(maxsize=1)
def codescientist_repo() -> Path:
    return require("codescientist")


@lru_cache(maxsize=1)
def meta_analysis() -> tuple[list[dict], str]:
    """(entries, file name) of the with-expert-notes meta-analysis JSON."""
    files = sorted((codescientist_repo() / "metaanalysis").glob(META_GLOB))
    if len(files) != 1:
        raise RuntimeError(f"expected one {META_GLOB}, found {len(files)}")
    return json.loads(files[0].read_text(encoding="utf-8")), files[0].name


def judgements() -> dict[str, dict[str, str]]:
    """idea -> {run key: judgement} from the meta-analysis per-run judgements
    (support / refute / inconclusive)."""
    out: dict[str, dict[str, str]] = {}
    entries, _ = meta_analysis()
    for e in entries:
        ma = e.get("meta-analysis") or {}
        idea = key_of_experiment_name(ma.get("experiment_name") or e["idea"]["research_idea_name"])
        runs = out.setdefault(idea, {})
        for j in ma.get("support_refute_inconclusive_judgements") or []:
            runs[key_of_experiment_name(j["specific_experiment_name"])] = j["judgement"].strip().lower()
    return out


def reviews() -> dict[str, list[tuple[str, str]]]:
    """paper short name -> [(soundness label, novelty label)] for the 60 external ratings."""
    p = codescientist_repo() / REVIEWS
    rows = list(csv.reader(p.open(encoding="utf-8"), delimiter="\t"))
    out: dict[str, list[tuple[str, str]]] = {}
    for r in rows[1:]:
        name = r[0].split(" - ", 1)[1].strip()
        out.setdefault(name, []).append((r[1].split(":")[0].strip(), r[2].split(":")[0].strip()))
    return out


def soundness_score(labels: list[tuple[str, str]]) -> float:
    """The paper's binarisation: Unsound -> 0, every other soundness label -> 1; averaged."""
    return sum(0 if s == "Unsound" else 1 for s, _ in labels) / len(labels)


@lru_cache(maxsize=1)
def examples_zip() -> zipfile.ZipFile:
    return zipfile.ZipFile(require("codescientist-example-experiments"))


@lru_cache(maxsize=1)
def full50_zip() -> zipfile.ZipFile:
    return zipfile.ZipFile(require("codescientist-full50"))


def example_dirs() -> list[str]:
    z = examples_zip()
    return sorted({n[len(EXAMPLES_PREFIX):].split("/", 1)[0] for n in z.namelist()
                   if n.startswith(EXAMPLES_PREFIX) and n.count("/") >= 2})


def full50_prefix() -> str:
    """The archive's single top-level folder (the with-expert-notes batch), plus "/"."""
    tops = {n.split("/", 1)[0] for n in full50_zip().namelist()}
    if len(tops) != 1:
        raise RuntimeError(f"full50 archive: expected one top-level folder, found {len(tops)}")
    top = tops.pop()
    if "withexpertnotes" not in top:
        raise RuntimeError("full50 archive: top folder is not the with-expert-notes batch")
    return top + "/"


def full50_dirs() -> list[str]:
    z = full50_zip()
    pre = full50_prefix()
    return sorted({n[len(pre):].split("/", 1)[0] for n in z.namelist()
                   if n.startswith(pre) and n.count("/") >= 2})


def audit_dir(zf: zipfile.ZipFile, prefix: str, dirname: str,
              reruns: list[str] | None = None) -> dict:
    """Audit one experiment directory inside a zip; return its node entry."""
    t = Tree(zf=zf, prefix=prefix + dirname)
    run = Run(run=dirname, format="codescientist")
    run.nodes.append(load_codescientist_experiment(
        t, node_id=dirname, reruns=reruns,
        rerun_source="meta-analysis per-run judgements" if reruns else None,
        inputs=run.inputs))
    data, _ = audit(run)
    node = data["nodes"][0]
    node["inputs"] = data["inputs"]
    return node


ERROR_CODES = ("U1", "A1", "A3", "A4", "R1", "R4", "R5")


def error_flagged(node: dict) -> bool:
    return any(c["severity"] == "error" for c in node["checks"])


def flagged_codes(node: dict, severities=("error", "warning")) -> list[str]:
    return sorted({c["code"] for c in node["checks"] if c["severity"] in severities})
