"""Adapter for the released Theorizer theories (the HTML export of a theory store).

Input: one condition directory of the released archive (for example
``html_output-literature-supported-accuracy-focused/``), as written by asta-theorizer's
``src/ExportTheoryStoreAsHTML.py``:

- ``theories/theory-<n>.html``: one theory; each law is a section headed
  ``<h3>Statement <i>: <name></h3>`` with ``Statement:``, ``Domain/Scope:`` (or the
  empty note ``Not specified.``) and a "Supporting Evidence for this Law" list whose
  items carry evidence links ``<a href="../results/<extraction>.html#<id>">[<id>]</a>``
  (or the empty note ``No evidence provided.``), then optional links to external
  evaluations (``../predictiveaccuracy/pe-*.html``).
- ``results/extraction-result-<n>.html``: one extraction from one paper; each evidence
  record is a ``<div class="extraction-instance-container" id="e<n>.<k>">`` holding a
  table of field names and values.
- ``predictiveaccuracy/pe-*.html``: the predictive-accuracy evaluation of one law, with
  per-prediction counts of papers that support, contradict or give no evidence.

The export maps each evidence ID to its extraction file and, when the ID has no entry in
that map, falls back silently to the ID itself as the file name (asta-theorizer
``src/ExportTheoryStoreAsHTML.py`` line 286 at commit c4802aa:
``extraction_id = uuid_to_extraction_id.get(uuid, uuid)``), so an unmapped ID still
renders as a link, to ``../results/<id>.html``, a file that does not exist. Why an ID is
unmapped upstream is not visible in the export and is not inferred here.

Checks
- **T1** an evidence ID cited by a law that resolves to no evidence record in the same
  condition directory (no ``id="<id>"`` container in any results file).
- **T2** a law with an empty scope (``Not specified.``) or an empty evidence list
  (``No evidence provided.``).
- **W1** and **W2** between each law statement and the text of the evidence records it
  cites (all resolved records, concatenated), and between each evidence item (the text
  the theory gives for one item, IDs removed) and the records that item cites.

Every finding carries a receipt: the SHA-256 of the theory HTML file and the character
offsets of the law section (or of the evidence link, for T1).
"""

from __future__ import annotations

import html as _html
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from consilience_ai2.core.findings import Finding, Receipt
from consilience_ai2.core.hashing import sha256_text
from consilience_ai2.core.numbers import NumberToken, extract_numbers
from consilience_ai2.receipts.claims import (
    CertaintyProfile,
    certainty_profile,
    certainty_upgrade,
    number_overreach,
)

EVIDENCE_ID = re.compile(r"^e\d+\.\d+$")
_TAG = re.compile(r"<[^>]+>")
_INSTANCE = re.compile(r'<div class="extraction-instance-container" id="([^"]+)">')
_ROW = re.compile(r"<tr>\s*<td><strong>(.*?)</strong></td>\s*<td>(.*?)</td>\s*</tr>", re.S)
_LAW_HEAD = re.compile(r"<h3>Statement (\d+): (.*?)</h3>", re.S)
_STATEMENT = re.compile(r"<p><strong>Statement:</strong>(.*?)</p>", re.S)
_SCOPE = re.compile(r"<p><strong>Domain/Scope:</strong>(.*?)</p>", re.S)
_EVIDENCE_HEAD = "<h4>Supporting Evidence for this Law</h4>"
_LI = re.compile(r"<li>(.*?)</li>", re.S)
_LINK = re.compile(r'<a href="([^"]*)" class="evidence-link">\[([^\]]*)\]</a>')
_PE_LINK = re.compile(r'href="\.\./(predictiveaccuracy/pe-[^"]+\.html)"')
_THEORY_NAME = re.compile(r"<p><strong>Name:</strong>(.*?)</p>", re.S)
_EMPTY_NOTE = re.compile(r'^\s*<span class="empty-note">.*?</span>\s*$', re.S)
_PE_TABLE = re.compile(
    r"<td><strong>Counts \(# of papers\)</strong></td>\s*<td>(\d+)</td>\s*<td>(\d+)</td>"
    r"\s*<td>(\d+)</td>", re.S)
_PE_THEORY = re.compile(r"<p><strong>Theory ID:</strong>\s*([^<]+)</p>")
_EID_IN_TEXT = re.compile(r"\be\d+\.\d+\b")


def strip_html(s: str) -> str:
    return " ".join(_html.unescape(_TAG.sub(" ", s)).split())


# --------------------------------------------------------------------------- records


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    file: str  # relative to the condition directory
    start: int
    end: int
    file_sha256: str
    fields: tuple[tuple[str, str], ...]

    @property
    def text(self) -> str:
        """The record's field values, one per line (field names are not included)."""
        return "\n".join(v for _, v in self.fields if v)


def parse_results_file(text: str, rel: str) -> list[EvidenceRecord]:
    sha = sha256_text(text)
    marks = list(_INSTANCE.finditer(text))
    out: list[EvidenceRecord] = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        chunk = text[m.start():end]
        fields = tuple((strip_html(a), strip_html(b)) for a, b in _ROW.findall(chunk))
        out.append(EvidenceRecord(m.group(1), rel, m.start(), end, sha, fields))
    return out


def load_records(condition_dir: Path) -> tuple[dict[str, EvidenceRecord], dict[str, Any]]:
    """Every evidence record in ``<condition>/results/``, keyed by ID, with counts."""
    records: dict[str, EvidenceRecord] = {}
    files = sorted((condition_dir / "results").glob("*.html")) if (
        condition_dir / "results").is_dir() else []
    duplicates = 0
    empty_files = 0
    for p in files:
        text = p.read_text(encoding="utf-8")
        recs = parse_results_file(text, f"results/{p.name}")
        if not recs:
            empty_files += 1
        for r in recs:
            if r.id in records:
                duplicates += 1
                continue
            records[r.id] = r
    return records, {"results_files": len(files), "records": len(records),
                     "duplicate_ids": duplicates, "files_without_records": empty_files}


# --------------------------------------------------------------------------- theories


@dataclass(frozen=True)
class EvidenceItem:
    text: str  # the item's text with links removed
    ids: tuple[str, ...]
    hrefs: tuple[str, ...]
    id_offsets: tuple[tuple[int, int], ...]  # offsets of each link in the theory file


@dataclass
class Law:
    index: int
    name: str
    statement: str | None
    scope: str | None  # None when the export shows the empty note
    evidence_empty: bool  # the export shows "No evidence provided."
    items: list[EvidenceItem]
    start: int
    end: int
    pe_file: str | None

    @property
    def ids(self) -> list[str]:
        seen: list[str] = []
        for it in self.items:
            for i in it.ids:
                if i not in seen:
                    seen.append(i)
        return seen


@dataclass
class Theory:
    id: str
    name: str
    file: str
    sha256: str
    laws: list[Law] = field(default_factory=list)


def _section_value(rx: re.Pattern[str], chunk: str) -> tuple[str | None, bool]:
    """(text, is_empty_note) for the first match of ``rx`` in ``chunk``."""
    m = rx.search(chunk)
    if not m:
        return None, False
    raw = m.group(1)
    if _EMPTY_NOTE.match(raw):
        return None, True
    t = strip_html(raw)
    return (t or None), not t


def parse_theory(text: str, rel: str) -> Theory:
    tid = Path(rel).stem
    nm = _THEORY_NAME.search(text)
    theory = Theory(tid, strip_html(nm.group(1)) if nm else "", rel, sha256_text(text))
    heads = list(_LAW_HEAD.finditer(text))
    stop_all = text.find("<h2>Theory (Additional Details)</h2>")
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else (
            stop_all if stop_all > h.start() else len(text))
        chunk = text[h.start():end]
        statement, _ = _section_value(_STATEMENT, chunk)
        scope, _ = _section_value(_SCOPE, chunk)
        items: list[EvidenceItem] = []
        ev_empty = False
        k = chunk.find(_EVIDENCE_HEAD)
        if k != -1:
            rest = chunk[k + len(_EVIDENCE_HEAD):]
            nxt = rest.find("<h4>")
            block = rest[:nxt] if nxt != -1 else rest
            block_off = h.start() + k + len(_EVIDENCE_HEAD)
            if "No evidence provided." in block and "<li>" not in block:
                ev_empty = True
            for li in _LI.finditer(block):
                body = li.group(1)
                links = list(_LINK.finditer(body))
                base = block_off + li.start(1)
                items.append(EvidenceItem(
                    text=strip_html(_LINK.sub(" ", body)),
                    ids=tuple(lk.group(2) for lk in links),
                    hrefs=tuple(lk.group(1) for lk in links),
                    id_offsets=tuple((base + lk.start(), base + lk.end()) for lk in links),
                ))
            if not items and not ev_empty:
                ev_empty = True
        else:
            ev_empty = True
        pe = _PE_LINK.search(chunk)
        theory.laws.append(Law(int(h.group(1)), strip_html(h.group(2)), statement, scope,
                               ev_empty, items, h.start(), end, pe.group(1) if pe else None))
    return theory


def iter_theories(condition_dir: Path) -> Iterator[Theory]:
    tdir = condition_dir / "theories"
    files = sorted(tdir.glob("theory-*.html"),
                   key=lambda p: (int(p.stem.split("-")[1]) if p.stem.split("-")[1].isdigit()
                                  else 0, p.name))
    for p in files:
        yield parse_theory(p.read_text(encoding="utf-8"), f"theories/{p.name}")


# --------------------------------------------------------------------------- predictive accuracy


@dataclass(frozen=True)
class PredictiveAccuracy:
    file: str
    theory_id: str | None
    support: int
    contradict: int
    no_evidence: int
    predictions: int


def parse_predictive_accuracy(text: str, rel: str) -> PredictiveAccuracy:
    rows = _PE_TABLE.findall(text)
    tm = _PE_THEORY.search(text)
    return PredictiveAccuracy(
        rel, tm.group(1).strip() if tm else None,
        sum(int(a) for a, _, _ in rows), sum(int(b) for _, b, _ in rows),
        sum(int(c) for _, _, c in rows), len(rows))


# --------------------------------------------------------------------------- checks


@dataclass
class LawResult:
    """The checks for one law, for aggregation."""

    theory: str
    law: int
    ids: int
    unresolved: list[str]
    empty_scope: bool
    empty_evidence: bool
    w1: bool | None  # None when no record resolved (nothing to compare)
    w2: bool | None
    w1_items: int  # evidence items flagged W1
    w2_items: int
    items_checked: int  # items with at least one resolved record
    items_with_ids: int
    items_without_ids: int
    numbers_in_statement: int
    pe_file: str | None


def _receipt(source: str, sha: str, a: int, b: int) -> Receipt:
    return Receipt(source, sha, offset=a, end=b)


class RecordCache:
    """Number tokens and certainty profiles per evidence record, computed once.

    A source made of several records is read record by record: its numbers are the
    union of the records' numbers and its hedged and assertive words are the
    concatenation of each record's (a negation never reaches across records).
    """

    def __init__(self) -> None:
        self._tokens: dict[str, list[NumberToken]] = {}
        self._profiles: dict[str, CertaintyProfile] = {}

    def tokens(self, recs: list[EvidenceRecord]) -> list[NumberToken]:
        out: list[NumberToken] = []
        for r in recs:
            if r.id not in self._tokens:
                self._tokens[r.id] = extract_numbers(r.text)
            out.extend(self._tokens[r.id])
        return out

    def profile(self, recs: list[EvidenceRecord]) -> CertaintyProfile:
        h: list[str] = []
        a: list[str] = []
        n: list[str] = []
        for r in recs:
            if r.id not in self._profiles:
                self._profiles[r.id] = certainty_profile(r.text)
            p = self._profiles[r.id]
            h.extend(p.hedged)
            a.extend(p.assertive)
            n.extend(p.negated_assertive)
        return CertaintyProfile(tuple(h), tuple(a), tuple(n))


def check_theory(theory: Theory, records: dict[str, EvidenceRecord], condition: str,
                 emit_info: bool = False, cache: RecordCache | None = None,
                 ) -> tuple[list[Finding], list[LawResult]]:
    """T1, T2, W1 and W2 for every law of ``theory`` against ``records``."""
    cache = cache or RecordCache()
    findings: list[Finding] = []
    results: list[LawResult] = []
    src = f"theorizer:{condition}/{theory.file}"
    for law in theory.laws:
        rec = _receipt(src, theory.sha256, law.start, law.end)
        key = f"{theory.id}#statement-{law.index}"
        unresolved: list[str] = []
        for it in law.items:
            for eid, (a, b), href in zip(it.ids, it.id_offsets, it.hrefs, strict=True):
                if eid not in records:
                    unresolved.append(eid)
                    findings.append(Finding(
                        "T1", "error", f"evidence ID {eid} resolves to no evidence record",
                        file=f"{condition}/{theory.file}", key=key,
                        receipt=_receipt(src, theory.sha256, a, b),
                        details={"id": eid, "href": href,
                                 "well_formed": bool(EVIDENCE_ID.match(eid))}))
        empty_scope = law.scope is None
        if empty_scope or law.evidence_empty:
            what = [w for w, on in (("empty scope", empty_scope),
                                    ("empty evidence list", law.evidence_empty)) if on]
            findings.append(Finding(
                "T2", "error", f"law {law.index} has an " + " and an ".join(what),
                file=f"{condition}/{theory.file}", key=key, receipt=rec,
                details={"empty_scope": empty_scope, "empty_evidence": law.evidence_empty}))
        resolved = [records[i] for i in law.ids if i in records]
        w1 = w2 = None
        n_stmt = 0
        if law.statement:
            n_stmt = len(extract_numbers(law.statement))
        if resolved and law.statement:
            c1 = number_overreach(law.statement, "", cache.tokens(resolved))
            c2 = certainty_upgrade(law.statement, "", cache.profile(resolved))
            w1, w2 = c1.flagged, c2.flagged
            if c1.flagged:
                findings.append(Finding(
                    "W1", "warning", "number in the law not in its cited evidence: "
                    + ", ".join(t.text for t in c1.unsupported),
                    file=f"{condition}/{theory.file}", key=key, receipt=rec,
                    details={"level": "law", "ids": [r.id for r in resolved], **c1.details()}))
            if c2.flagged:
                findings.append(Finding(
                    "W2", "warning", "certainty upgrade from cited evidence to law",
                    file=f"{condition}/{theory.file}", key=key, receipt=rec,
                    details={"level": "law", "ids": [r.id for r in resolved], **c2.details()}))
        w1_items = w2_items = checked = with_ids = without_ids = 0
        for n, it in enumerate(law.items):
            if it.ids:
                with_ids += 1
            else:
                without_ids += 1
            recs = [records[i] for i in it.ids if i in records]
            claim = _EID_IN_TEXT.sub(" ", it.text)
            if not recs or not claim.strip():
                continue
            checked += 1
            c1 = number_overreach(claim, "", cache.tokens(recs))
            c2 = certainty_upgrade(claim, "", cache.profile(recs))
            a, b = (it.id_offsets[0][0], it.id_offsets[-1][1]) if it.id_offsets else (
                law.start, law.end)
            irec = _receipt(src, theory.sha256, a, b)
            if c1.flagged:
                w1_items += 1
                findings.append(Finding(
                    "W1", "warning", f"evidence item {n + 1}: number not in its cited records: "
                    + ", ".join(t.text for t in c1.unsupported),
                    file=f"{condition}/{theory.file}", key=f"{key}/item-{n + 1}", receipt=irec,
                    details={"level": "item", "ids": list(it.ids), **c1.details()}))
            if c2.flagged:
                w2_items += 1
                findings.append(Finding(
                    "W2", "warning", f"evidence item {n + 1}: certainty upgrade from its records",
                    file=f"{condition}/{theory.file}", key=f"{key}/item-{n + 1}", receipt=irec,
                    details={"level": "item", "ids": list(it.ids), **c2.details()}))
        if emit_info and not unresolved and law.ids:
            findings.append(Finding(
                "T1", "info", f"all {len(law.ids)} evidence IDs resolve",
                file=f"{condition}/{theory.file}", key=key, receipt=rec))
        results.append(LawResult(
            theory.id, law.index, len(law.ids), sorted(set(unresolved)), empty_scope,
            law.evidence_empty,
            w1, w2, w1_items, w2_items, checked, with_ids, without_ids, n_stmt, law.pe_file))
    return findings, results
