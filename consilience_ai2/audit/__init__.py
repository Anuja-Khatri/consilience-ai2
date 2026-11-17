"""C2 experiment audit: deterministic, receipt-backed checks of agent-run experiments.

    from consilience_ai2.audit import audit_path
    data, report = audit_path("out_dir")          # format detected
    data["nodes"][0]["verdict"]                     # "pass" | "flag" | "refuse"

It runs beside AutoDiscovery's language-model "Validity Check" and does not replace it:
that review text is hashed and kept beside each verdict, never judged. No language model
is called; the same input gives byte-identical output. See docs/audit.md for every code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from consilience_ai2.audit.adapters import (
    Tree,
    detect_format,
    load_autodiscovery,
    load_codescientist,
)
from consilience_ai2.audit.engine import RULES, RULES_VERSION, audit
from consilience_ai2.audit.model import Node, Run, TextField
from consilience_ai2.core.findings import Report


def load(path: str | Path, format: str | None = None, metadata: str | Path | None = None
         ) -> Run:
    fmt = format or detect_format(path)
    if fmt == "autodiscovery":
        return load_autodiscovery(path, metadata=metadata)
    if fmt == "codescientist":
        return load_codescientist(path)
    raise ValueError(f"unknown format {fmt!r} (autodiscovery or codescientist)")


def audit_path(path: str | Path, format: str | None = None,
               metadata: str | Path | None = None) -> tuple[dict[str, Any], Report]:
    """Load ``path`` with the right adapter and audit it."""
    return audit(load(path, format=format, metadata=metadata))


__all__ = ["RULES", "RULES_VERSION", "Node", "Run", "TextField", "Tree", "audit", "audit_path",
           "detect_format", "load", "load_autodiscovery", "load_codescientist"]
