"""Local source text for the E6 verbatim check.

``--sources`` names one of three things (detected from what is at the path):

- a **directory** of text files: ``<name>.txt`` or ``<name>.md``, where ``<name>`` is an
  evidence entry's ``cite`` key or its ``provenance.corpus_id``, tried in that order.
  Receipt source ``file:<file name>``; SHA-256 of the file bytes.
- a Theorizer **PaperStore** JSON (``{"paperstore_lut": ..., "paperstore": ...}``, the
  format ``PaperStore.save`` writes): looked up by ``provenance.corpus_id`` through the
  key ``paper-<corpus_id>``; the text is the paper's ``paper_markdown`` when its
  ``status`` is ``full-text``. Receipt source ``paperstore:<corpus_id>``; SHA-256 of
  that text (UTF-8).
- an AutoDiscovery exploration **index.json** (``{"experiments": [...]}``, written by
  the asta-flows ``runlog.py``): looked up by the entry's ``source`` field
  ``"run <label>, experiment <n>"``; the text is the experiment's hypothesis, analysis
  and review joined by spaces, as that workflow's ``check.py`` builds it. Receipt source
  ``autodiscovery:experiment-<n>``; SHA-256 of that text.

Offsets in receipts are character offsets into the text as decoded (UTF-8).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from consilience_ai2.core.hashing import sha256_file, sha256_text

_AD_SOURCE = re.compile(r"run (\w+), experiment (\d+)")


@dataclass(frozen=True)
class SourceText:
    source_id: str
    text: str
    sha256: str
    path: Path | None = None  # the file read, when the text is a whole file


@dataclass(frozen=True)
class Lookup:
    """A source lookup: the text when found, else the reason it is uncheckable."""

    found: SourceText | None
    reason: str | None = None
    tried: tuple[str, ...] = ()


class SourceError(ValueError):
    """The --sources path cannot be read."""


class SourceStore:
    kind = "none"

    def lookup(self, cite: str | None, entry: dict[str, Any] | None) -> Lookup:
        return Lookup(None, "no local source text was given (--sources)")

    def describe(self) -> dict[str, Any]:
        return {"kind": self.kind}


def _corpus_id(entry: dict[str, Any] | None) -> str | None:
    if not isinstance(entry, dict):
        return None
    prov = entry.get("provenance")
    if isinstance(prov, dict):
        cid = prov.get("corpus_id")
        if isinstance(cid, str) and cid.strip():
            return cid.strip()
    return None


class TextDirStore(SourceStore):
    kind = "directory"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, Path] = {}
        for p in sorted(root.iterdir()):
            if p.is_file() and p.suffix in (".txt", ".md"):
                self.files.setdefault(p.stem, p)
        self._cache: dict[Path, SourceText] = {}

    def _read(self, p: Path) -> SourceText:
        if p not in self._cache:
            self._cache[p] = SourceText(f"file:{p.name}", p.read_text(encoding="utf-8"),
                                        sha256_file(p), p)
        return self._cache[p]

    def lookup(self, cite: str | None, entry: dict[str, Any] | None) -> Lookup:
        names = [n for n in (cite, _corpus_id(entry)) if n]
        if not names:
            return Lookup(None, "the evidence has no cite key or provenance.corpus_id to look up")
        for n in names:
            if n in self.files:
                return Lookup(self._read(self.files[n]), tried=tuple(names))
        return Lookup(None, f"no {' or '.join(n + '.txt' for n in names)} in the sources directory",
                      tuple(names))

    def describe(self) -> dict[str, Any]:
        return {"kind": self.kind, "files": len(self.files)}


class PaperStoreStore(SourceStore):
    kind = "paperstore"

    def __init__(self, data: dict[str, Any]) -> None:
        self.lut = data.get("paperstore_lut") or {}
        self.papers = data.get("paperstore") or {}

    def lookup(self, cite: str | None, entry: dict[str, Any] | None) -> Lookup:
        cid = _corpus_id(entry)
        if cid is None:
            return Lookup(None, "a PaperStore is looked up by provenance.corpus_id, and the "
                                "evidence has none")
        key = f"paper-{cid}"
        primary = self.lut.get(key, key)
        paper = self.papers.get(primary)
        if not isinstance(paper, dict):
            return Lookup(None, f"corpus_id {cid} is not in the PaperStore", (cid,))
        text = paper.get("paper_markdown")
        if paper.get("status") != "full-text" or not isinstance(text, str) or not text.strip():
            return Lookup(None, f"corpus_id {cid} has no full text in the PaperStore "
                                f"(status {paper.get('status')!r})", (cid,))
        return Lookup(SourceText(f"paperstore:{cid}", text, sha256_text(text)), tried=(cid,))

    def describe(self) -> dict[str, Any]:
        return {"kind": self.kind, "papers": len(self.papers)}


class AutoDiscoveryIndexStore(SourceStore):
    kind = "autodiscovery-index"

    def __init__(self, data: dict[str, Any]) -> None:
        self.experiments: dict[int, dict[str, Any]] = {}
        for e in data.get("experiments") or []:
            if isinstance(e, dict) and isinstance(e.get("experiment"), int):
                self.experiments[e["experiment"]] = e

    def lookup(self, cite: str | None, entry: dict[str, Any] | None) -> Lookup:
        src = entry.get("source") if isinstance(entry, dict) else None
        m = _AD_SOURCE.search(src) if isinstance(src, str) else None
        if not m:
            return Lookup(None, 'the evidence has no source "run <label>, experiment <n>"')
        n = int(m.group(2))
        e = self.experiments.get(n)
        if e is None:
            return Lookup(None, f"experiment {n} is not in the index", (str(n),))
        text = " ".join([str(e.get("hypothesis") or ""), str(e.get("analysis") or ""),
                         str(e.get("review") or "")])
        return Lookup(SourceText(f"autodiscovery:experiment-{n}", text, sha256_text(text)),
                      tried=(str(n),))

    def describe(self) -> dict[str, Any]:
        return {"kind": self.kind, "experiments": len(self.experiments)}


def open_sources(path: str | Path | None) -> SourceStore:
    """The store for ``--sources`` (a directory or a JSON file), or an empty store."""
    if path is None:
        return SourceStore()
    p = Path(path)
    if p.is_dir():
        return TextDirStore(p)
    if not p.is_file():
        raise SourceError(f"--sources {p}: no such file or directory")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceError(f"--sources {p}: not JSON ({exc})") from exc
    if isinstance(data, dict) and "paperstore" in data:
        return PaperStoreStore(data)
    if isinstance(data, dict) and "experiments" in data:
        return AutoDiscoveryIndexStore(data)
    raise SourceError(f"--sources {p}: neither a PaperStore JSON nor an AutoDiscovery index.json")
