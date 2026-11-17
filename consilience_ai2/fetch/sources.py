"""The pinned source list (``sources.yaml``) and the local cache location."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

SOURCES_FILE = "sources.yaml"
_KINDS = ("file", "git")


class SourceError(ValueError):
    """A malformed source entry, an unknown source name, or an unsafe cache root."""


@dataclass(frozen=True)
class Source:
    name: str
    kind: str
    url: str
    path: str
    licence: str
    citation: str
    sha256: str | None = None
    size: int | None = None
    commit: str | None = None
    extract: bool = False
    page: str | None = None
    manual: str | None = None
    used_for: str | None = None
    local_names: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_todo(self) -> bool:
        """A file source whose hash is not pinned yet: it is never fetched."""
        return self.kind == "file" and (self.sha256 is None or self.sha256.startswith("TODO"))

    def local_candidates(self) -> tuple[str, ...]:
        """File names (or repo directory names) to look for in a --from-dir folder."""
        if self.kind == "git":
            return (self.url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git"),)
        return self.local_names or (Path(self.path).name,)

    def extract_dir(self, root: Path) -> Path | None:
        if self.kind != "file" or not self.path.endswith(".zip"):
            return None
        return root / self.path[: -len(".zip")]


def _parse(entry: dict[str, Any]) -> Source:
    for key in ("name", "kind", "url", "path", "licence", "citation"):
        if not entry.get(key):
            raise SourceError(f"source {entry.get('name', '?')!r}: missing {key!r}")
    kind = entry["kind"]
    if kind not in _KINDS:
        raise SourceError(f"source {entry['name']!r}: kind must be one of {_KINDS}")
    if kind == "git" and not (isinstance(entry.get("commit"), str) and len(entry["commit"]) == 40):
        raise SourceError(f"source {entry['name']!r}: a git source pins a full 40-char commit")
    if kind == "file" and not entry.get("sha256"):
        raise SourceError(f"source {entry['name']!r}: a file source needs sha256 (or 'TODO: ...')")
    path = entry["path"]
    if Path(path).is_absolute() or ".." in Path(path).parts:
        raise SourceError(f"source {entry['name']!r}: path must be relative to the cache root")
    known = {f for f in Source.__dataclass_fields__}
    unknown = set(entry) - known
    if unknown:
        raise SourceError(f"source {entry['name']!r}: unknown keys {sorted(unknown)}")
    kw = dict(entry)
    kw["local_names"] = tuple(entry.get("local_names") or ())
    kw["extract"] = bool(entry.get("extract", False))
    return Source(**kw)


def load_sources(path: str | Path | None = None) -> dict[str, Source]:
    """All sources, by name, from the packaged ``sources.yaml`` (or ``path``)."""
    if path is None:
        text = resources.files("consilience_ai2.fetch").joinpath(SOURCES_FILE).read_text("utf-8")
    else:
        text = Path(path).read_text("utf-8")
    data = yaml.safe_load(text)
    if data.get("schema_version") != 1:
        raise SourceError("sources.yaml: schema_version must be 1")
    out: dict[str, Source] = {}
    for entry in data.get("sources", []):
        src = _parse(entry)
        if src.name in out:
            raise SourceError(f"duplicate source name {src.name!r}")
        out[src.name] = src
    return out


def get_source(name: str) -> Source:
    sources = load_sources()
    if name not in sources:
        raise SourceError(f"unknown source {name!r}; known: {', '.join(sorted(sources))}")
    return sources[name]


def _repo_root() -> Path | None:
    """The source checkout this package runs from, if it runs from one."""
    here = Path(__file__).resolve().parent.parent.parent
    if (here / "pyproject.toml").is_file() and (here / "consilience_ai2").is_dir():
        return here
    return None


def cache_root(override: str | Path | None = None) -> Path:
    """The cache root: ``override``, else ``$CONSILIENCE_AI2_DATA``, else
    ``~/.cache/consilience-ai2``. A root inside the source checkout is refused, so data
    can never end up committed."""
    raw = override or os.environ.get("CONSILIENCE_AI2_DATA") or "~/.cache/consilience-ai2"
    root = Path(raw).expanduser().resolve()
    repo = _repo_root()
    if repo is not None and (root == repo or repo in root.parents):
        raise SourceError(f"cache root {root} is inside the repository {repo}; refusing "
                          "(data must never be stored in the repo)")
    return root


def source_path(name: str, root: str | Path | None = None) -> Path:
    """Where source ``name`` lives in the cache (it may not be fetched yet)."""
    return cache_root(root) / get_source(name).path
