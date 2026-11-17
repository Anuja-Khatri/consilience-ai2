"""The Asta workspace checker: E1-E6, W1 and W2 over ``evidence.yml``, ``references.bib``
and the ``.ev`` spans of every ``.qmd`` file.

What is read, mirroring Quarto and the asta-plugins evidence filter
(``plugins/asta-tools/skills/workspace/assets/_extensions/evidence/snippet.lua``):

- The evidence store: the files named under ``metadata-files`` in ``_quarto.yml`` (in
  order, a later file's entry replacing an earlier one with the same key); with no
  ``_quarto.yml``, ``evidence.yml`` at the workspace root. A ``.qmd`` file's own front
  matter may add or replace entries under ``evidence:`` for that file. Only entries that
  are maps are stored, as in the filter.
- The bibliography: ``bibliography`` in ``_quarto.yml`` and in each file's front matter
  (a path or a list); with no ``_quarto.yml``, ``references.bib`` at the root.
- Every ``*.qmd`` under the workspace, skipping directories whose names start with
  ``.`` or ``_`` (``_extensions``, ``_site``, ``.quarto``) and ``node_modules``.
- For each ``.ev`` span the filter resolves each field from the inline attribute first,
  then the stored entry (``key``). An empty value counts as absent.

Codes (severity): E0 unreadable input (error) or a file named in ``_quarto.yml`` or front
matter that does not exist (warning), E1 unknown key (error), E2 no resolvable
quote (error), E3 ``cite`` not in the bibliography (error), E4 orphaned entry (error),
E5 provenance format (error), E6 verbatim check (``NOT_FOUND`` error; ``FOUND`` and
``UNCHECKABLE`` info), W1 number overreach (warning), W2 certainty upgrade (warning).
The run fails (exit 1) on any error.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from consilience_ai2 import __version__
from consilience_ai2.core.findings import Finding, InputRecord, Receipt, Report
from consilience_ai2.core.hashing import sha256_text
from consilience_ai2.core.normalise import NORMALISATION_VERSION, find_normalised
from consilience_ai2.receipts.claims import certainty_upgrade, certainty_words, number_overreach
from consilience_ai2.receipts.qmd import Span, find_spans, front_matter, plain_text
from consilience_ai2.receipts.sources import SourceStore, open_sources
from consilience_ai2.receipts.yamlnodes import YamlError, load_with_lines

TOOL = "consilience-ai2 receipts"
FIELDS = ("quote", "cite", "source", "url", "locator")
PROV_FIELDS = ("method", "query", "corpus_id", "url", "retrieved", "note")
URL_SCHEMES = ("http", "https", "asta")
_SKIP_DIRS = {"node_modules"}
_BIB_ENTRY = re.compile(r"@\s*([A-Za-z]+)\s*[{(]\s*([^,\s{}()]+)\s*,")
_BIB_NOT_ENTRY = {"string", "preamble", "comment"}
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")
_SUBWORD = re.compile(r"^[a-z][a-z0-9-]*$")


# --------------------------------------------------------------------------- data


@dataclass(frozen=True)
class AstaMethods:
    version: str
    commands: frozenset[str]
    passthrough: tuple[str, ...]

    def accepts(self, method: str) -> bool:
        if method in self.commands:
            return True
        for p in self.passthrough:
            if method == p:
                return True
            if method.startswith(p + " "):
                rest = method[len(p) + 1:].split(" ")
                return all(_SUBWORD.match(w) for w in rest)
        return False


@lru_cache(maxsize=1)
def asta_methods() -> AstaMethods:
    raw = json.loads(resources.files("consilience_ai2.receipts").joinpath(
        "data/asta_methods.json").read_text(encoding="utf-8"))
    return AstaMethods(raw["version"], frozenset(raw["commands"]), tuple(raw["passthrough"]))


@dataclass
class Entry:
    key: str
    fields: dict[str, Any]
    file: str
    line: int
    field_lines: dict[str, int] = field(default_factory=dict)
    scope: str | None = None  # None = project store; else the .qmd that defines it
    extra_bib: frozenset[str] = frozenset()  # keys from that .qmd's own bibliography


@dataclass
class EvSpan:
    file: str
    span: Span
    key: str | None
    entry: Entry | None
    quote: str | None
    cite: str | None
    cite_inline: bool


# --------------------------------------------------------------------------- helpers


def _rel(p: Path, root: Path) -> str:
    return p.relative_to(root).as_posix()


def _as_list(v: Any) -> list[str]:
    if isinstance(v, str):
        return [v] if v.strip() else []
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str) and x.strip()]
    return []


def _text(v: Any) -> str | None:
    """A stored field as the filter reads it: a non-empty string, else absent."""
    if isinstance(v, str):
        s = v.strip()
        return v if s else None
    return None


def bib_keys(text: str) -> set[str]:
    """Entry keys of a BibTeX file (``@type{key,``); ``@string``, ``@preamble`` and
    ``@comment`` are not entries."""
    return {m.group(2) for m in _BIB_ENTRY.finditer(text)
            if m.group(1).lower() not in _BIB_NOT_ENTRY}


def qmd_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*.qmd")):
        parts = p.relative_to(root).parts[:-1]
        if any(x.startswith((".", "_")) or x in _SKIP_DIRS for x in parts):
            continue
        out.append(p)
    return out


def valid_iso_date(s: str) -> bool:
    if not _ISO_DATE.match(s):
        return False
    try:
        _dt.date.fromisoformat(s)
    except ValueError:
        return False
    return True


# --------------------------------------------------------------------------- checker


class WorkspaceChecker:
    """Collects inputs, then runs every check. Use ``check_workspace`` for one call."""

    def __init__(self, root: Path, sources: SourceStore) -> None:
        self.root = root
        self.sources = sources
        self.report = Report(tool=TOOL, tool_version=__version__)
        self.store: dict[str, Entry] = {}
        self.bib: set[str] = set()
        self.bib_files: list[str] = []
        self.spans: list[EvSpan] = []
        self.doc_entries: list[Entry] = []
        self.used_bib: dict[str, set[str]] = {}  # project entry key -> bibs of documents using it
        self._inputs: dict[tuple[str, str], InputRecord] = {}

    # ---- inputs

    def _input(self, p: Path, role: str) -> None:
        rel = _rel(p, self.root) if p.is_relative_to(self.root) else p.as_posix()
        k = (rel, role)
        if k not in self._inputs:
            rec = InputRecord.from_file(p, role=role)
            self._inputs[k] = InputRecord(rel, rec.sha256, role)

    def _e0(self, file: str | None, message: str, line: int | None = None,
            severity: str = "error") -> None:
        self.report.add(Finding("E0", severity, message, file=file, line=line))

    def _read(self, p: Path) -> str | None:
        try:
            return p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self._e0(_rel(p, self.root) if p.is_relative_to(self.root) else str(p),
                     f"cannot read: {exc}")
            return None

    def _load_entries(self, data: Any, lines: dict[tuple[str, ...], int], file: str,
                      scope: str | None) -> dict[str, Entry]:
        out: dict[str, Entry] = {}
        ev = data.get("evidence") if isinstance(data, dict) else None
        if not isinstance(ev, dict):
            return out
        for key, val in ev.items():
            if not isinstance(val, dict):
                continue  # the filter stores only map entries
            fl = {f: lines.get(("evidence", key, f), lines.get(("evidence", key), 1))
                  for f in val}
            prov = val.get("provenance")
            if isinstance(prov, dict):
                for f in prov:
                    fl[f"provenance.{f}"] = lines.get(("evidence", key, "provenance", f),
                                                      fl.get("provenance", 1))
            out[key] = Entry(key, val, file, lines.get(("evidence", key), 1), fl, scope)
        return out

    def _load_yaml_file(self, p: Path, role: str) -> tuple[Any, dict] | None:
        text = self._read(p)
        if text is None:
            return None
        self._input(p, role)
        try:
            return load_with_lines(text)
        except YamlError as exc:
            self._e0(_rel(p, self.root), f"not valid YAML: {exc}")
            return None

    def load_project(self) -> None:
        qy = self.root / "_quarto.yml"
        meta_files: list[str]
        bibs: list[str]
        if qy.is_file():
            loaded = self._load_yaml_file(qy, "quarto")
            q = loaded[0] if loaded else None
            q = q if isinstance(q, dict) else {}
            meta_files = _as_list(q.get("metadata-files"))
            bibs = _as_list(q.get("bibliography"))
            if loaded and isinstance(q, dict) and isinstance(q.get("evidence"), dict):
                for k, e in self._load_entries(q, loaded[1], "_quarto.yml", None).items():
                    self.store[k] = e
        else:
            meta_files = ["evidence.yml"] if (self.root / "evidence.yml").is_file() else []
            bibs = ["references.bib"] if (self.root / "references.bib").is_file() else []
        for mf in meta_files:
            p = self.root / mf
            if not p.is_file():
                self._e0("_quarto.yml", f"metadata-files lists {mf}, which does not exist",
                         severity="warning")
                continue
            loaded = self._load_yaml_file(p, "evidence")
            if loaded is None:
                continue
            for k, e in self._load_entries(loaded[0], loaded[1], _rel(p, self.root), None).items():
                self.store[k] = e
        for b in bibs:
            self._load_bib(self.root / b, "_quarto.yml")

    def _load_bib(self, p: Path, named_in: str, project: bool = True) -> set[str]:
        if not p.is_file():
            self._e0(named_in, f"bibliography {p.name} does not exist", severity="warning")
            return set()
        text = self._read(p)
        if text is None:
            return set()
        self._input(p, "bibliography")
        keys = bib_keys(text)
        rel = _rel(p, self.root) if p.is_relative_to(self.root) else str(p)
        if rel not in self.bib_files:
            self.bib_files.append(rel)
        if project:
            self.bib |= keys
        return keys

    def load_documents(self) -> None:
        for p in qmd_files(self.root):
            text = self._read(p)
            if text is None:
                continue
            rel = _rel(p, self.root)
            self._input(p, "document")
            store = dict(self.store)
            bib = set(self.bib)
            fm = front_matter(text)
            if fm is not None:
                try:
                    data, lines = load_with_lines(fm[0], first_line=fm[1])
                except YamlError as exc:
                    self._e0(rel, f"front matter is not valid YAML: {exc}", line=1)
                    data, lines = None, {}
                local = self._load_entries(data, lines, rel, rel)
                doc_bib: set[str] = set()
                if isinstance(data, dict):
                    for b in _as_list(data.get("bibliography")):
                        doc_bib |= self._load_bib(p.parent / b, rel, project=False)
                bib |= doc_bib
                for e in local.values():
                    e.extra_bib = frozenset(doc_bib)
                self.doc_entries.extend(local.values())
                store.update(local)
            for s in find_spans(text):
                key = s.attr("key")
                entry = store.get(key) if key else None
                q_inline = s.attr("quote")
                quote = q_inline if q_inline is not None else (
                    _text(entry.fields.get("quote")) if entry else None)
                c_inline = s.attr("cite")
                cite = c_inline if c_inline is not None else (
                    _text(entry.fields.get("cite")) if entry else None)
                ev = EvSpan(rel, s, key, entry, quote, cite, c_inline is not None)
                if entry is not None and entry.scope is None:
                    self.used_bib.setdefault(entry.key, set()).update(bib - self.bib)
                self.spans.append(ev)
                self._check_span(ev, bib)

    # ---- per-span checks: E1, E2, E3 (inline cite), E6, W1, W2

    def _check_span(self, ev: EvSpan, bib: set[str]) -> None:
        s = ev.span
        claim = plain_text(s.content)
        if ev.key and ev.entry is None:
            self.report.add(Finding(
                "E1", "error", f'.ev span references unknown key "{ev.key}"',
                file=ev.file, line=s.line, key=ev.key,
                details={"claim": claim}))
        if ev.quote is None:
            self.report.add(Finding(
                "E2", "error", ".ev span has no quote (inline quote= or a stored entry's quote)",
                file=ev.file, line=s.line, key=ev.key, details={"claim": claim}))
        if ev.cite_inline and ev.cite not in bib:
            self.report.add(Finding(
                "E3", "error", f'cite "{ev.cite}" is not a key in the bibliography',
                file=ev.file, line=s.line, key=ev.key,
                details={"cite": ev.cite, "bibliography": sorted(self.bib_files)}))
        if ev.quote is None:
            return
        self._check_verbatim(ev)
        qid = f"quote:{ev.file}:{s.line}" if ev.key is None else f"evidence:{ev.key}"
        receipt = Receipt(qid, sha256_text(ev.quote))
        w1 = number_overreach(claim, ev.quote)
        if w1.flagged:
            self.report.add(Finding(
                "W1", "warning",
                "number in the claim not in the quote: " + ", ".join(t.text for t in w1.unsupported),
                file=ev.file, line=s.line, key=ev.key, receipt=receipt,
                details={"claim": claim, **w1.details()}))
        w2 = certainty_upgrade(claim, ev.quote)
        if w2.flagged:
            self.report.add(Finding(
                "W2", "warning",
                f"certainty upgrade: claim says {', '.join(w2.claim.assertive)}; quote says "
                f"{', '.join(w2.source.hedged)}",
                file=ev.file, line=s.line, key=ev.key, receipt=receipt,
                details={"claim": claim, **w2.details()}))

    def _check_verbatim(self, ev: EvSpan) -> None:
        assert ev.quote is not None
        entry_fields = ev.entry.fields if ev.entry else None
        if entry_fields is None and ev.span.attr("source"):
            entry_fields = {"source": ev.span.attr("source")}
        look = self.sources.lookup(ev.cite, entry_fields)
        if look.found is None:
            self.report.add(Finding(
                "E6", "info", f"UNCHECKABLE: {look.reason}", file=ev.file, line=ev.span.line,
                key=ev.key, details={"outcome": "UNCHECKABLE", "tried": list(look.tried)}))
            return
        st = look.found
        if st.path is not None:
            self._input(st.path, "source")
        hits = find_normalised(ev.quote, st.text)
        if hits:
            a, b = hits[0]
            self.report.add(Finding(
                "E6", "info", f"FOUND in {st.source_id} at [{a}, {b})",
                file=ev.file, line=ev.span.line, key=ev.key,
                receipt=Receipt(st.source_id, st.sha256, offset=a, end=b,
                                normalisation=NORMALISATION_VERSION),
                details={"outcome": "FOUND", "occurrences": len(hits)}))
        else:
            self.report.add(Finding(
                "E6", "error", f"NOT_FOUND: the quote is not verbatim in {st.source_id}",
                file=ev.file, line=ev.span.line, key=ev.key,
                receipt=Receipt(st.source_id, st.sha256, normalisation=NORMALISATION_VERSION),
                details={"outcome": "NOT_FOUND"}))

    # ---- per-entry checks: E3 (stored cite), E4, E5

    def check_entries(self) -> None:
        used: dict[tuple[str | None, str], int] = {}
        for ev in self.spans:
            if ev.entry is not None:
                k = (ev.entry.scope, ev.entry.key)
                used[k] = used.get(k, 0) + 1
        entries = list(self.store.values()) + self.doc_entries
        for e in sorted(entries, key=lambda x: (x.file, x.line, x.key)):
            cite = _text(e.fields.get("cite"))
            doc_bibs = e.extra_bib if e.scope else self.used_bib.get(e.key, set())
            if cite is not None and cite not in self.bib and cite not in doc_bibs:
                self.report.add(Finding(
                    "E3", "error", f'cite "{cite}" is not a key in the bibliography',
                    file=e.file, line=e.field_lines.get("cite", e.line), key=e.key,
                    details={"cite": cite, "bibliography": sorted(self.bib_files)}))
            if used.get((e.scope, e.key), 0) == 0:
                self.report.add(Finding(
                    "E4", "error", f'evidence entry "{e.key}" is referenced by no .ev span',
                    file=e.file, line=e.line, key=e.key))
            self._check_provenance(e)

    def _e5(self, e: Entry, fld: str, message: str, value: Any) -> None:
        self.report.add(Finding(
            "E5", "error", message, file=e.file,
            line=e.field_lines.get(f"provenance.{fld}", e.field_lines.get("provenance", e.line)),
            key=e.key, details={"field": fld, "value": value if isinstance(value, str) else None}))

    def _check_provenance(self, e: Entry) -> None:
        if "provenance" not in e.fields:
            return
        prov = e.fields["provenance"]
        if not isinstance(prov, dict):
            self._e5(e, "provenance", "provenance is not a map", None)
            return
        methods = asta_methods()
        m = prov.get("method")
        if "method" in prov and not (isinstance(m, str) and methods.accepts(m.strip())
                                     and m == m.strip()):
            self._e5(e, "method", f"provenance.method {m!r} is not an exact asta subcommand", m)
        c = prov.get("corpus_id")
        if "corpus_id" in prov and not (isinstance(c, str) and c.isascii() and c.isdigit()):
            self._e5(e, "corpus_id", f"provenance.corpus_id {c!r} is not an integer", c)
        u = prov.get("url")
        if "url" in prov:
            sm = _SCHEME.match(u) if isinstance(u, str) else None
            if not sm or sm.group(1).lower() not in URL_SCHEMES:
                self._e5(e, "url", f"provenance.url {u!r} does not use http, https or asta", u)
        r = prov.get("retrieved")
        if "retrieved" in prov and not (isinstance(r, str) and valid_iso_date(r)):
            self._e5(e, "retrieved", f"provenance.retrieved {r!r} is not an ISO date (YYYY-MM-DD)", r)

    # ---- run

    def run(self) -> Report:
        if not self.root.is_dir():
            self._e0(None, f"workspace {self.root} is not a directory")
            return self.report
        self.load_project()
        self.load_documents()
        self.check_entries()
        self.report.inputs = [self._inputs[k] for k in sorted(self._inputs)]
        self.report.extra = {
            "checked_spans": len(self.spans),
            "entries": len(self.store) + len(self.doc_entries),
            "sources": self.sources.describe(),
            "rules": {
                "normalisation": NORMALISATION_VERSION,
                "certainty_words": certainty_words().version,
                "asta_methods": asta_methods().version,
            },
        }
        return self.report


def check_workspace(root: str | Path, sources: str | Path | SourceStore | None = None) -> Report:
    """Run E0-E6, W1 and W2 on the workspace at ``root``; return the report."""
    store = sources if isinstance(sources, SourceStore) else open_sources(sources)
    return WorkspaceChecker(Path(root).resolve(), store).run()
