"""The ``consilience-ai2`` command. Subcommands are discovered, not listed here:
see ``consilience_ai2.core.registry``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from consilience_ai2 import __version__
from consilience_ai2.core.registry import discover

EPILOG = ("Independent work, not affiliated with or endorsed by the Allen Institute for AI "
          "(Ai2). Exit codes: 0 pass, 1 findings or failure, 2 usage error.")


def build_parser() -> tuple[argparse.ArgumentParser, list[str]]:
    parser = argparse.ArgumentParser(
        prog="consilience-ai2",
        description="Deterministic validity checks for agent-produced science.",
        epilog=EPILOG,
    )
    parser.add_argument("--version", action="version", version=f"consilience-ai2 {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    names = discover(sub)
    return parser, names


def main(argv: Sequence[str] | None = None) -> int:
    parser, _ = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return int(func(args) or 0)
    except BrokenPipeError:  # e.g. piped into `head`
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
