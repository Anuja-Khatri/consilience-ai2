"""Findings, receipts and reports: the one output schema every component writes.

- ``Receipt``: what was checked: a source id, the SHA-256 of the source bytes, the
  character span ``[offset, end)`` checked (when there is one) and the normalisation
  version used (when text was normalised). Passing checks emit receipts too.
- ``Finding``: one result: a stable ``code`` (``E1``, ``A5``, ``V1``...), a
  ``severity`` (``error`` | ``warning`` | ``info``), a message, where it is
  (``file``, ``line``, ``key``), an optional ``receipt`` and optional ``details``
  (component-specific, JSON-serialisable).
- ``Report``: the tool name and version, the inputs read (each with its SHA-256), the
  findings, and summary counts by severity and by code. ``extra`` holds
  component-specific top-level fields (for example ``checked_spans``).

Determinism: ``Report.to_json()`` sorts keys, sorts findings by
``(file, line, code, key, message)``, writes no timestamp unless one is passed in as
``created``, and refuses NaN. The same inputs give byte-identical reports.

GitHub annotations: ``Finding.to_annotation()`` renders the workflow-command form used
by ``quarto-check.sh`` in asta-plugins, e.g. ``::error file=index.qmd,line=42::E1 ...``;
``info`` maps to ``notice``. Values are escaped as GitHub documents.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from consilience_ai2.core.hashing import sha256_file

REPORT_VERSION = 1
SEVERITIES = ("error", "warning", "info")
_ANNOTATION_LEVEL = {"error": "error", "warning": "warning", "info": "notice"}
_CODE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RESERVED = {"version", "tool", "tool_version", "inputs", "findings", "summary", "created"}


def _check_json(value: Any, what: str) -> None:
    try:
        json.dumps(value, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{what} is not JSON-serialisable without NaN: {exc}") from exc


@dataclass(frozen=True)
class Receipt:
    """What a check looked at. ``sha256`` is None only when the source could not be read
    (then the finding should say UNCHECKABLE)."""

    source: str
    sha256: str | None
    offset: int | None = None
    end: int | None = None
    normalisation: str | None = None

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("receipt.source must be a non-empty id")
        if self.sha256 is not None and not _SHA256.match(self.sha256):
            raise ValueError(f"receipt.sha256 must be 64 lowercase hex chars: {self.sha256!r}")
        if self.offset is not None and self.offset < 0:
            raise ValueError("receipt.offset must be >= 0")
        if self.end is not None and (self.offset is None or self.end < self.offset):
            raise ValueError("receipt.end needs an offset and must be >= offset")

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "sha256": self.sha256, "offset": self.offset,
                "end": self.end, "normalisation": self.normalisation}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Receipt:
        return cls(source=d["source"], sha256=d.get("sha256"), offset=d.get("offset"),
                   end=d.get("end"), normalisation=d.get("normalisation"))


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    file: str | None = None
    line: int | None = None
    key: str | None = None
    receipt: Receipt | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _CODE.match(self.code):
            raise ValueError(f"finding.code must match {_CODE.pattern}: {self.code!r}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"finding.severity must be one of {SEVERITIES}: {self.severity!r}")
        if self.line is not None and self.line < 1:
            raise ValueError("finding.line is 1-based")
        _check_json(dict(self.details), "finding.details")

    def sort_key(self) -> tuple:
        return (self.file or "", self.line or 0, self.code, self.key or "", self.message)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "code": self.code, "severity": self.severity, "message": self.message,
            "file": self.file, "line": self.line, "key": self.key,
            "receipt": self.receipt.to_dict() if self.receipt else None,
        }
        if self.details:
            d["details"] = dict(self.details)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Finding:
        r = d.get("receipt")
        return cls(code=d["code"], severity=d["severity"], message=d["message"],
                   file=d.get("file"), line=d.get("line"), key=d.get("key"),
                   receipt=Receipt.from_dict(r) if r else None,
                   details=dict(d.get("details") or {}))

    def to_annotation(self) -> str:
        """One GitHub workflow-command line for this finding."""
        level = _ANNOTATION_LEVEL[self.severity]
        props = []
        if self.file:
            props.append(f"file={_escape_property(self.file)}")
            if self.line is not None:
                props.append(f"line={self.line}")
        head = f"::{level}" + (" " + ",".join(props) if props else "")
        return f"{head}::{_escape_data(f'{self.code} {self.message}')}"


def _escape_data(s: str) -> str:
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(s: str) -> str:
    return _escape_data(s).replace(":", "%3A").replace(",", "%2C")


@dataclass(frozen=True)
class InputRecord:
    """An input the tool read: a path or id, the SHA-256 of its bytes, and its role."""

    path: str
    sha256: str | None
    role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "role": self.role}

    @classmethod
    def from_file(cls, path: str | Path, role: str | None = None,
                  relative_to: str | Path | None = None) -> InputRecord:
        p = Path(path)
        shown = p.relative_to(relative_to).as_posix() if relative_to else p.as_posix()
        return cls(path=shown, sha256=sha256_file(p), role=role)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> InputRecord:
        return cls(path=d["path"], sha256=d.get("sha256"), role=d.get("role"))


@dataclass
class Report:
    tool: str
    tool_version: str
    inputs: list[InputRecord] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    created: str | None = None  # only when the caller passes one; never defaulted

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def extend(self, findings: Iterable[Finding]) -> None:
        self.findings.extend(findings)

    def sorted_findings(self) -> list[Finding]:
        return sorted(self.findings, key=Finding.sort_key)

    def summary(self) -> dict[str, Any]:
        by_sev = Counter(f.severity for f in self.findings)
        by_code = Counter(f.code for f in self.findings)
        return {
            "total": len(self.findings),
            "by_severity": {s: by_sev.get(s, 0) for s in SEVERITIES},
            "by_code": dict(sorted(by_code.items())),
        }

    def exit_code(self, fail_on: Iterable[str] = ("error",)) -> int:
        """0 when no finding has a severity in ``fail_on``, else 1."""
        bad = set(fail_on)
        return 1 if any(f.severity in bad for f in self.findings) else 0

    def to_dict(self) -> dict[str, Any]:
        clash = _RESERVED & set(self.extra)
        if clash:
            raise ValueError(f"report.extra may not override {sorted(clash)}")
        _check_json(self.extra, "report.extra")
        d: dict[str, Any] = {
            "version": REPORT_VERSION,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "inputs": [i.to_dict() for i in sorted(self.inputs, key=lambda i: (i.path, i.role or ""))],
            "findings": [f.to_dict() for f in self.sorted_findings()],
            "summary": self.summary(),
        }
        if self.created is not None:
            d["created"] = self.created
        d.update(self.extra)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, ensure_ascii=False,
                          allow_nan=False) + "\n"

    def write(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")
        return p

    def annotations(self) -> list[str]:
        return [f.to_annotation() for f in self.sorted_findings()]

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Report:
        if d.get("version") != REPORT_VERSION:
            raise ValueError(f"unsupported report version {d.get('version')!r}")
        known = _RESERVED
        return cls(
            tool=d["tool"], tool_version=d["tool_version"],
            inputs=[InputRecord.from_dict(i) for i in d.get("inputs", [])],
            findings=[Finding.from_dict(f) for f in d.get("findings", [])],
            extra={k: v for k, v in d.items() if k not in known},
            created=d.get("created"),
        )
