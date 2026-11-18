"""Run every check on one record and build ``reproduction_verdict.json``.

Codes (stable): ``S1`` record unreadable or not schema-valid (nothing else runs);
``F1`` faithfulness; ``D1`` decidability; ``V1`` verdict from the numbers; ``P1``
commit order; ``P2`` verbatim hypothesis copy. Severities: an ``error`` fails the run
(exit 1): S1, F1 ``substitution`` or ``not_comparable``, P1 proven post hoc, P2
``reworded``. A ``warning`` marks what the reader must know but is not a defect of the
record by itself: F1 ``proxy``, D1 not decidable, V1 when the prose verdict
(``reported_verdict``) differs from the numbers, P1 not shown, P2 uncheckable.
Everything else is ``info`` with a receipt. ``reproduced`` / ``not_reproduced`` /
``inconclusive`` are results, not defects, and never change the exit code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from consilience_ai2 import __version__
from consilience_ai2.core.findings import Finding, InputRecord, Receipt, Report
from consilience_ai2.core.hashing import sha256_file, sha256_json, sha256_text
from consilience_ai2.core.normalise import NORMALISATION_VERSION
from consilience_ai2.reproduce.comparability import check_faithfulness, resolve_backend
from consilience_ai2.reproduce.decide import (
    DEFAULT_RULE,
    check_decidability,
    check_hypothesis,
    check_verdict,
)
from consilience_ai2.reproduce.gitorder import check_commit_order
from consilience_ai2.reproduce.record import RecordError, load_file, parse

TOOL = "consilience-ai2 reproduce"
RUBRIC = ("asta-flows secondary reproduction: Faithfulness, Decidability, Outcome "
          "(plugins/asta-flows/skills/run-workflow/workflows/secondary-reproduction.md)")
CHECKS = ("F1", "D1", "V1", "P1", "P2")


def _key_lines(text: str) -> dict[str, int]:
    """Line (1-based) of each top-level key, for annotations. Empty when not YAML."""
    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        return {}
    if not isinstance(node, yaml.MappingNode):
        return {}
    return {k.value: k.start_mark.line + 1 for k, _ in node.value
            if isinstance(k, yaml.ScalarNode)}


def evaluate(data: dict[str, Any], *, record_path: str | Path | None = None,
             repo: str | Path | None = None, backend: str = "auto", pack: str | None = None,
             skip: tuple[str, ...] = (), file_sha256: str | None = None,
             display: str | None = None, lines: dict[str, int] | None = None,
             rule: str = DEFAULT_RULE) -> Report:
    """Check one record (already loaded as a dict). See ``check_file`` for a path.
    ``rule`` is the V1 verdict rule: ``v0.2`` (the source's finding, default) or
    ``v0.1`` (the declared direction); see ``decide``."""
    be = resolve_backend(backend)
    shown = display or (Path(record_path).name if record_path else "<record>")
    try:
        sha = file_sha256 or sha256_json(data)
    except (TypeError, ValueError) as exc:
        report = Report(tool=TOOL, tool_version=__version__)
        report.add(Finding("S1", "error", f"record not valid: not plain JSON data ({exc})",
                           file=shown, line=1))
        report.extra.update({"record": {"path": shown, "sha256": None, "id": None},
                             "verdict": None, "rubric": RUBRIC})
        return report
    lines = lines or {}
    report = Report(tool=TOOL, tool_version=__version__)
    if record_path is not None:
        report.inputs.append(InputRecord(path=shown, sha256=sha, role="reproduction_record"))
    rid = data.get("id") if isinstance(data, dict) and isinstance(data.get("id"), str) else None

    def receipt(field: str) -> Receipt:
        return Receipt(f"record:{shown}#{field}", sha)

    try:
        rec = parse(data, path=record_path, file_sha256=sha)
    except RecordError as exc:
        report.add(Finding("S1", "error", f"record not valid: {exc}", file=shown, line=1,
                           key=rid, receipt=receipt("$")))
        report.extra.update({"record": {"path": shown, "sha256": sha, "id": rid},
                             "verdict": None, "rubric": RUBRIC})
        return report

    out: dict[str, Any] = {}
    caveats: list[str] = []

    f1 = check_faithfulness(rec, be, pack)
    sev = {"same_quantity": "info", "proxy": "warning"}.get(f1.cls, "error")
    caveats += f1.caveats
    if "F1" not in skip:
        report.add(Finding(
            "F1", sev, f"faithfulness: {f1.label}", file=shown,
            line=lines.get("reproduction"), key=rid, receipt=receipt("reproduction"),
            details={"faithfulness": f1.label, "class": f1.cls, "declared": f1.declared,
                     "mismatches": f1.mismatches, "backend": f1.backend}))
    out["faithfulness"] = f1.label

    d1 = check_decidability(rec, be)
    if "D1" not in skip:
        report.add(Finding(
            "D1", "info" if d1.cls == "decidable" else "warning",
            f"decidability: {d1.cls}" + (f" ({d1.reason})" if d1.reason else ""),
            file=shown, line=lines.get("reproduction"), key=rid,
            receipt=receipt("reproduction"),
            details={"decidability": d1.cls, "reason": d1.reason, **d1.details}))
    out["decidability"] = d1.cls

    v1 = check_verdict(rec, f1, d1, be, rule)
    reported = rec.data.get("reported_verdict")
    agrees = None if reported is None else reported == v1.outcome
    if "V1" not in skip:
        msg = f"verdict from the numbers: {v1.verdict} ({v1.label})"
        if agrees is False:
            msg += f"; the reported verdict says {reported}"
        report.add(Finding(
            "V1", "warning" if agrees is False else "info", msg, file=shown,
            line=lines.get("thresholds"), key=rid, receipt=receipt("thresholds"),
            details={"verdict": v1.verdict, "outcome": v1.outcome, "reason": v1.reason,
                     "caveats": caveats, "reported_verdict": reported,
                     "reported_agrees": agrees, **v1.details}))
    out.update({"outcome": v1.outcome, "outcome_label": v1.label, "verdict": v1.verdict,
                "reason": v1.reason, "verdict_rule": rule})

    if "P1" not in skip:
        p1 = check_commit_order(rec.data, record_path, repo)
        sev = "info" if p1.cls != "thresholds_post_hoc" else (
            "error" if p1.proven else "warning")
        report.add(Finding(
            "P1", sev, f"commit order: {p1.cls}" + (f" ({p1.reason})" if p1.reason else ""),
            file=shown, line=lines.get("thresholds"), key=rid,
            receipt=receipt("thresholds.committed"),
            details={"commit_order": p1.cls, "reason": p1.reason, "method": p1.method,
                     **p1.details}))
        out["commit_order"] = p1.cls if p1.reason is None or p1.cls != "thresholds_post_hoc" \
            else f"{p1.cls}({p1.reason})"

    if "P2" not in skip:
        p2 = check_hypothesis(rec)
        sev = {"verbatim": "info", "reworded": "error"}.get(p2.cls, "warning")
        src_h = rec.data.get("source_hypothesis") or ""
        report.add(Finding(
            "P2", sev, f"hypothesis copy: {p2.cls}", file=shown, line=lines.get("hypothesis"),
            key=rid,
            receipt=Receipt(f"record:{shown}#source_hypothesis", sha256_text(src_h),
                            normalisation=NORMALISATION_VERSION),
            details={"hypothesis_copy": p2.cls,
                     "first_difference_normalised_offset": p2.first_difference,
                     "hypothesis_sha256": sha256_text(rec.data.get("hypothesis") or "")}))
        out["hypothesis_copy"] = p2.cls

    out["caveats"] = caveats
    report.extra.update({"record": {"path": shown, "sha256": sha, "id": rid},
                         "verdict": out, "rubric": RUBRIC,
                         "checks_skipped": sorted(set(skip) & set(CHECKS))})
    return report


def check_file(path: str | Path, *, repo: str | Path | None = None, backend: str = "auto",
               pack: str | None = None, skip: tuple[str, ...] = (),
               rule: str = DEFAULT_RULE) -> Report:
    """Check a record file (YAML or JSON)."""
    p = Path(path)
    try:
        data = load_file(p)
    except RecordError as exc:
        report = Report(tool=TOOL, tool_version=__version__)
        sha = sha256_file(p) if p.is_file() else None
        report.inputs.append(InputRecord(path=p.name, sha256=sha, role="reproduction_record"))
        report.add(Finding("S1", "error", f"record not readable: {exc}", file=p.name,
                           receipt=Receipt(f"record:{p.name}", sha)))
        report.extra.update({"record": {"path": p.name, "sha256": sha, "id": None},
                             "verdict": None, "rubric": RUBRIC})
        return report
    text = p.read_text(encoding="utf-8")
    return evaluate(data, record_path=p, repo=repo, backend=backend, pack=pack, skip=skip,
                    file_sha256=sha256_file(p), display=p.name, lines=_key_lines(text),
                    rule=rule)
