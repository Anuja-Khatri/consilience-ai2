"""Read LaTeX ``tabular`` tables from a report and compare their cells with recomputed
values at the printed precision (a number receipt for a whole table)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from consilience_ai2.core.numbers import agrees_at_printed_precision, extract_numbers

_TABULAR = re.compile(r"\\begin\{tabular\}(?:\[[^\]]*\])?\{[^}]*\}(.*?)\\end\{tabular\}", re.S)
_RULES = re.compile(r"\\(?:toprule|midrule|bottomrule|hline|cline\{[^}]*\})")


@dataclass(frozen=True)
class Table:
    rows: list[list[str]]
    start: int
    end: int

    @property
    def header(self) -> list[str]:
        return self.rows[0] if self.rows else []

    def body(self) -> list[list[str]]:
        return self.rows[1:]


def latex_tables(text: str) -> list[Table]:
    """Every ``tabular`` in ``text``: rows split on ``\\\\``, cells on ``&``, rules dropped."""
    out = []
    for m in _TABULAR.finditer(text):
        body = _RULES.sub("", m.group(1))
        rows = []
        for raw in body.split("\\\\"):
            cells = [c.strip() for c in raw.split("&")]
            if any(cells):
                rows.append(cells)
        out.append(Table(rows, m.start(), m.end()))
    return out


def cell_agrees(cell: str, value: float) -> bool | None:
    """True/False when the cell holds exactly one number; None when it holds none or
    several (uncheckable, never a mismatch)."""
    toks = [t for t in extract_numbers(cell) if t.ok and t.role == "value"]
    if len(toks) != 1:
        return None
    return agrees_at_printed_precision(toks[0], value)
