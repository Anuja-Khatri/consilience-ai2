"""CLI auto-discovery: core finds each component's subcommands; no edit when one is added.

The component list is fixed: ``COMPONENTS = ("receipts", "audit", "reproduce", "fetch")``.
For each name, ``discover`` imports ``consilience_ai2.<name>.cli`` and calls its
``register(subparsers)``. A component that is not there yet (no subpackage, or no
``cli.py``) is skipped quietly, so the skeleton and every partial branch still run. Any
other import error is NOT hidden: a component that exists but fails to import is a bug
and is raised.

The contract for ``<component>/cli.py``::

    def register(subparsers) -> None:
        p = subparsers.add_parser("<component>", help="...", description="...")
        p.add_argument(...)
        p.set_defaults(func=run)        # run(args: argparse.Namespace) -> int (exit code)
"""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Sequence

COMPONENTS: tuple[str, ...] = ("receipts", "audit", "reproduce", "fetch")
PACKAGE = "consilience_ai2"


def _is_missing(exc: ModuleNotFoundError, package: str, name: str) -> bool:
    """True only when the missing module is the component package or its cli module."""
    missing = exc.name or ""
    return missing in (f"{package}.{name}", f"{package}.{name}.cli")


def discover(subparsers: argparse._SubParsersAction,
             components: Sequence[str] = COMPONENTS,
             package: str = PACKAGE) -> list[str]:
    """Register every component that is present; return the names registered, in order."""
    registered: list[str] = []
    for name in components:
        modname = f"{package}.{name}.cli"
        try:
            mod = importlib.import_module(modname)
        except ModuleNotFoundError as exc:
            if _is_missing(exc, package, name):
                continue
            raise
        register = getattr(mod, "register", None)
        if not callable(register):
            raise TypeError(f"{modname} has no callable register(subparsers)")
        register(subparsers)
        registered.append(name)
    return registered
