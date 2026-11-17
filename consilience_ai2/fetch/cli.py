"""``consilience-ai2 fetch``: download pinned sources into the cache and verify them."""

from __future__ import annotations

import argparse
import sys

from consilience_ai2.fetch.get import FetchError, fetch_source, status
from consilience_ai2.fetch.sources import SourceError, cache_root, load_sources


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "fetch",
        help="download and verify pinned data sources (never into the repo)",
        description=(
            "Download pinned sources into $CONSILIENCE_AI2_DATA (default "
            "~/.cache/consilience-ai2) and verify each: files by SHA-256 and size, git "
            "repositories by commit. A mismatch is refused. Data is never stored in the "
            "repository."
        ),
    )
    p.add_argument("names", nargs="*", metavar="NAME",
                   help="source names, or 'all' (see --list)")
    p.add_argument("--list", action="store_true", help="list sources and their cache status")
    p.add_argument("--from-dir", action="append", default=[], metavar="DIR",
                   help="look for the file (or git clone) in DIR first; repeatable")
    p.add_argument("--offline", action="store_true",
                   help="never download; only copy in from --from-dir")
    p.add_argument("--verify", action="store_true", help="re-hash cached files")
    p.add_argument("--extract", dest="extract", action="store_true", default=None,
                   help="unzip zip sources even if sources.yaml says not to")
    p.add_argument("--no-extract", dest="extract", action="store_false",
                   help="do not unzip zip sources")
    p.add_argument("--cache", metavar="DIR", default=None,
                   help="cache root (overrides $CONSILIENCE_AI2_DATA)")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    try:
        sources = load_sources()
        root = cache_root(args.cache)
    except SourceError as exc:
        print(f"fetch: {exc}", file=sys.stderr)
        return 1
    if args.list or not args.names:
        print(f"cache root: {root}")
        for name, src in sorted(sources.items()):
            pin = src.commit[:12] if src.kind == "git" else (src.sha256 or "")[:12]
            size = f"{src.size} B" if src.size else ""
            print(f"  {name:36s} {src.kind:4s} {status(src, root):10s} {pin:12s} {size:>12s}  "
                  f"{src.path}")
        return 0 if args.list else 2
    names = sorted(sources) if args.names == ["all"] else args.names
    unknown = [n for n in names if n not in sources]
    if unknown:
        print(f"fetch: unknown source(s) {unknown}; known: {', '.join(sorted(sources))}",
              file=sys.stderr)
        return 2
    failed = 0
    for name in names:
        src = sources[name]
        try:
            path = fetch_source(src, root, args.from_dir, verify=args.verify,
                                extract_zip=args.extract, quiet=args.quiet,
                                offline=args.offline)
        except (FetchError, SourceError, OSError) as exc:
            failed += 1
            print(f"FAIL {name}: {exc}", file=sys.stderr)
            if src.manual:
                print(f"     manual step: {src.manual}", file=sys.stderr)
            continue
        pin = src.commit if src.kind == "git" else src.sha256
        print(f"ok   {name}  {pin}  {path}")
    return 1 if failed else 0
