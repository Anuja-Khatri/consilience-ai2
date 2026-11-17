"""Pinned downloads of the released Ai2 data this project measures on.

Python API (all paths are in the cache, never in the repository)::

    from consilience_ai2.fetch import require, ensure, ensure_extracted, source_path

    require("sciarena-eval")                     # verified path, no network; error if absent
    ensure("discoverybench")                     # fetch if needed, then verify
    ensure_extracted("theorizer-paper-data")     # the unzipped directory

See ``sources.yaml`` for every source, its pin, licence and citation.
"""

from consilience_ai2.fetch.get import (
    FetchError,
    ensure,
    ensure_extracted,
    fetch_source,
    require,
    status,
)
from consilience_ai2.fetch.sources import (
    Source,
    SourceError,
    cache_root,
    get_source,
    load_sources,
    source_path,
)

__all__ = [
    "FetchError", "Source", "SourceError", "cache_root", "ensure", "ensure_extracted",
    "fetch_source", "get_source", "load_sources", "require", "source_path", "status",
]
