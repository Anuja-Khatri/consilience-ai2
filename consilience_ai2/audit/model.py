"""The adapter-neutral model every check reads.

An adapter (AutoDiscovery, CodeScientist, DiscoveryBench) turns its native files into a
``Run`` of ``Node``s. A node carries:

- **claim fields**: text that states results (AutoDiscovery ``analysis`` and, when the
  reviewer passed the node, ``review``; a CodeScientist report). A1 checks their numbers.
- **context fields**: ``hypothesis`` and ``experiment_plan`` text (A2, A3).
- **evidence fields**: what the run actually printed or saved (``code_output``; a
  CodeScientist ``stdout``, ``log.json`` and ``results.json``).
- **code**: the program that ran (A2 constants, A3 columns, R4 literals, R5 slicing).

Each field remembers the file it came from and that file's SHA-256, so every finding can
carry a receipt. For a field taken from inside a JSON file (an AutoDiscovery node), the
receipt's offsets and line are relative to the field's decoded text; the receipt source
names the field (``mcts_node_2_1.json#analysis``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from consilience_ai2.core.hashing import sha256_text

CLAIM = "claim"
CONTEXT = "context"
EVIDENCE = "evidence"
CODE = "code"
KINDS = (CLAIM, CONTEXT, EVIDENCE, CODE)


@dataclass
class TextField:
    """One piece of text a check can read, with where it came from."""

    name: str              # e.g. "analysis", "report", "code_output", "results", "code"
    kind: str              # one of KINDS
    text: str
    file: str              # path relative to the run directory (or a member path)
    file_sha256: str       # SHA-256 of the file's bytes
    in_json: bool = False  # True when ``text`` is a decoded field of a JSON file
    mask: list[tuple[int, int]] = field(default_factory=list)  # spans not to read as claims

    @property
    def source(self) -> str:
        return f"{self.file}#{self.name}" if self.in_json else self.file

    @property
    def text_sha256(self) -> str:
        return sha256_text(self.text)

    def masked(self, start: int, end: int) -> bool:
        return any(s <= start < e or s < end <= e for s, e in self.mask)


@dataclass
class Node:
    """One experiment: an AutoDiscovery MCTS node or a CodeScientist experiment."""

    id: str
    fields: list[TextField] = field(default_factory=list)
    results: Any = None                 # parsed results JSON (CodeScientist), if any
    success: bool | None = None         # the LLM reviewer's pass flag, if any
    review_text: str | None = None      # hashed, never judged
    surprising: bool | None = None
    prior_mean: float | None = None
    posterior_mean: float | None = None
    reruns: list[str] | None = None     # verdict labels of reruns of the same idea (R2)
    rerun_source: str | None = None
    pilot_mode: str | None = None
    columns: set[str] | None = None     # dataset columns from the metadata (A3)
    columns_source: str | None = None
    uncheckable: str | None = None      # why nothing can be checked (verdict refuse)
    meta: dict[str, Any] = field(default_factory=dict)

    def of_kind(self, kind: str) -> list[TextField]:
        return [f for f in self.fields if f.kind == kind]

    def get(self, name: str) -> TextField | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None


@dataclass
class Run:
    """A run: the nodes the audit judges together (A5 shares one BH family per run)."""

    run: str
    format: str
    nodes: list[Node] = field(default_factory=list)
    inputs: list[tuple[str, str, str]] = field(default_factory=list)  # (path, sha256, role)
    notes: list[str] = field(default_factory=list)
