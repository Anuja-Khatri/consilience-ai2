"""Run every check over a ``Run`` and build ``validity_audit.json`` (version 1).

The file is a core ``Report`` (``version``, ``tool``, ``tool_version``, ``inputs``,
``findings``, ``summary``) with the needs-ledger section B.2 fields beside it:
``run``, ``n_nodes``, ``n_with_pvalue`` and ``nodes``; each node has ``id``,
``llm_validity_check`` (the reviewer's pass flag and the SHA-256 of its text, never
judged), ``checks``, ``q_value`` and ``verdict``; rules v0.2 adds ``verdict_level``
(``pass``, ``flag(warning)``, ``flag(error)``, ``refuse``) and ``notes`` (info notes on
reporting conventions, such as A7). ``parse_coverage`` reports how many
nodes had a p value the A5 parser could read, and ``rules`` states every code's status
(R5 included, with its scope).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from consilience_ai2 import __version__
from consilience_ai2.audit import stats
from consilience_ai2.audit.checks import (
    CLAIM_KINDS_NOTE,
    CODES,
    ERROR,
    EVIDENCE_NOTE,
    NODE_CHECKS,
    Check,
    build_context,
    check_a5,
    has_kind,
    notes,
    verdict,
    verdict_level,
)
from consilience_ai2.audit.model import CLAIM, EVIDENCE, Run
from consilience_ai2.core.findings import Finding, InputRecord, Receipt, Report
from consilience_ai2.core.hashing import sha256_text

TOOL = "consilience-ai2 audit"
RULES_VERSION = "audit-rules-2"

RULES: dict[str, dict[str, str]] = {
    "U1": {"status": "implemented", "severity": "error (verdict refuse)",
           "rule": "nothing to check: no printed output or results, or no claim text"},
    "A1": {"status": "implemented", "severity": "error / warning",
           "rule": "every decimal or percentage in a claim field is printed in the output, "
           "results, code or plan at its printed precision (x1, x100, /100), or derived as a "
           "worded relative change, ratio or difference of two such numbers of its sentence "
           "(info); agreeing only at a coarser precision, or possibly printed only in a saved "
           "figure, is a warning; in no output is an error"},
    "A2": {"status": "implemented", "severity": "warning",
           "rule": "stated n (n = N, N <unit>) vs n printed in the output vs integer n "
           "constants in the code"},
    "A3": {"status": "implemented", "severity": "error (code) / warning (hypothesis)",
           "rule": "columns read by the code, or snake_case/backticked names in the "
           "hypothesis, are in the dataset metadata (needs metadata)"},
    "A4": {"status": "implemented", "severity": "error",
           "rule": "'significant'/'surprising' (or a surprising node) needs a printed test "
           "statistic or p value"},
    "A5": {"status": "implemented", "severity": "warning",
           "rule": "Benjamini-Hochberg across all distinct p values parsed per node in the "
           f"run; surprising nodes with q > {stats.Q_THRESHOLD} flagged"},
    "A6": {"status": "implemented", "severity": "warning",
           "rule": "a surprising null is paired with its minimum detectable effect; flagged "
           f"when d_MDE > {stats.A6_MAX_MDE_D} or n is unknown"},
    "A7": {"status": "implemented", "severity": "info (reporting convention)",
           "rule": "an effect claim without a reported effect size gets an info note "
           "(details.status not_reported); it never flags"},
    "R1": {"status": "implemented", "severity": "error",
           "rule": "the only comparator named in comparison sentences is random or chance; a "
           "random comparator in a limiting or negative statement does not count"},
    "R2": {"status": "implemented", "severity": "error / warning",
           "rule": "support and refute verdicts both occur across reruns (needs rerun labels): "
           "an error when refutes are at least as many as supports, a warning otherwise"},
    "R3": {"status": "implemented", "severity": "warning",
           "rule": f"claim rests on n below {stats.R3_N_FLOOR} per group (80% power for d = "
           f"{stats.R3_EFFECT_D}, two-sided alpha {stats.ALPHA})"},
    "R4": {"status": "implemented", "severity": "error",
           "rule": "a reported number equals a literal (two or more significant digits) "
           "written in the code on the output path"},
    "R5": {"status": "implemented", "severity": "error",
           "rule": "a used top-level function or class that neither outputs nor is in the "
           "over-approximate backward slice of any output sink; scope: any printed or saved "
           "output, not the headline metric"},
}
VERDICTS = {"pass": "no error or warning (info only)",
            "flag(warning)": "at least one warning, no error",
            "flag(error)": "at least one error other than U1",
            "refuse": "U1: nothing can be checked"}


def _node_entry(node, checks: list[Check], q: float | None, na: list[str]) -> dict[str, Any]:
    llm = None
    if node.success is not None or node.review_text is not None:
        llm = {"success": node.success,
               "text_sha256": sha256_text(node.review_text) if node.review_text is not None
               else None}
    flagged = sorted({c.code for c in checks if c.severity in ("error", "warning")})
    return {
        "id": node.id,
        "llm_validity_check": llm,
        "checks": [c.to_dict() for c in sorted(
            checks, key=lambda c: (c.code, c.field or "", c.offset or 0, c.line or 0,
                                   c.message))],
        "codes": flagged,
        "not_applicable": na,
        "q_value": q,
        "verdict": verdict(checks, node.uncheckable is not None),
        "verdict_level": verdict_level(checks, node.uncheckable is not None),
        "notes": notes(checks),
        "surprising": node.surprising,
        "meta": node.meta,
    }


def audit(run: Run) -> tuple[dict[str, Any], Report]:
    """Audit every node; return (validity_audit dict, core Report)."""
    ctxs = {}
    per_node: dict[str, list[Check]] = {}
    na: dict[str, list[str]] = {}
    for node in run.nodes:
        if node.uncheckable is None:
            if not has_kind(node, EVIDENCE):
                node.uncheckable = "no printed output or results to check against"
            elif not has_kind(node, CLAIM):
                node.uncheckable = "no analysis or report text to check"
        checks: list[Check] = []
        if node.uncheckable is not None:
            checks.append(Check("U1", ERROR, f"uncheckable: {node.uncheckable}"))
            per_node[node.id] = checks
            na[node.id] = list(CODES)
            continue
        c = build_context(node)
        ctxs[node.id] = c
        missing = []
        for code, fn in NODE_CHECKS:
            got = fn(c)
            if not got:
                missing.append(code)
            checks.extend(got)
        per_node[node.id] = checks
        na[node.id] = missing
    a5, qmin, coverage = check_a5(run, ctxs)
    for nid, got in a5.items():
        per_node[nid].extend(got)
        if not got:
            na[nid].append("A5")
    for nid in na:
        na[nid] = sorted(set(na[nid]))
    nodes = [_node_entry(n, per_node[n.id], qmin.get(n.id), na[n.id]) for n in run.nodes]
    report = Report(tool=TOOL, tool_version=__version__,
                    inputs=[InputRecord(p, s, r) for p, s, r in run.inputs])
    for n in run.nodes:
        for c in per_node[n.id]:
            rec = None
            if c.source and c.sha256:
                rec = Receipt(c.source, c.sha256, offset=c.offset, end=c.end)
            report.add(Finding(c.code, c.severity, c.message, file=c.file, line=c.line,
                               key=n.id, receipt=rec, details=c.details))
    verdicts = [x["verdict"] for x in nodes]
    levels = [x["verdict_level"] for x in nodes]
    extra = {
        "run": run.run,
        "format": run.format,
        "rules_version": RULES_VERSION,
        "rules": RULES,
        "n_nodes": len(nodes),
        "n_with_pvalue": coverage["nodes_with_pvalue"],
        "parse_coverage": coverage,
        "verdicts": {v: verdicts.count(v) for v in ("pass", "flag", "refuse")},
        "verdict_levels": {v: levels.count(v) for v in VERDICTS},
        "verdict_mapping": VERDICTS,
        "nodes": nodes,
        "notes": run.notes + [CLAIM_KINDS_NOTE, EVIDENCE_NOTE],
    }
    report.extra = extra
    return report.to_dict(), report


def write(run: Run, out: str | Path) -> tuple[dict[str, Any], Report]:
    data, report = audit(run)
    report.write(out)
    return data, report
