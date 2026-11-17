#!/usr/bin/env python3
"""Build ``.claude-plugin/marketplace.json`` from per-plugin entry files.

The layout mirrors allenai/asta-plugins (pinned at a2dcade): one marketplace file at the
repository root, ``.claude-plugin/marketplace.json``, and each plugin under
``plugins/<name>/skills/<skill>/SKILL.md``, with NO per-plugin ``plugin.json`` (the
marketplace is the single metadata source).

So that each component can add its plugin without editing a shared file, a plugin
declares its marketplace entry in ``plugins/<name>/marketplace-entry.json``::

    {"name": "consilience-receipts",
     "description": "...",
     "keywords": ["evidence", "receipts"],
     "dependencies": []}                      # optional
     "strict": false                          # optional, default false

This script fills in ``source`` (``./plugins/<name>``), ``version`` (the package version
from pyproject.toml), ``author``, ``repository`` and ``license`` (MIT), and writes the
marketplace with plugins sorted by name.

``--check``           fail if the committed marketplace lists a plugin with no entry file,
                      or an entry differs from what the entry file generates; a plugin
                      not yet listed is a warning (the integrator runs ``make marketplace``)
``--check --strict``  also fail when the committed file is not exactly a fresh build
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
PLUGINS = REPO / "plugins"
ENTRY = "marketplace-entry.json"
OWNER = {"name": "Anuja Khatri"}
REPOSITORY = "https://github.com/Anuja-Khatri/consilience-ai2"
LICENSE = "MIT"
ALLOWED = {"name", "description", "keywords", "dependencies", "strict"}
_NAME = re.compile(r"^[a-z][a-z0-9\-]*$")


def version() -> str:
    return tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]


def load_entries() -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for f in sorted(PLUGINS.glob(f"*/{ENTRY}")):
        d = json.loads(f.read_text())
        plugin_dir = f.parent.name
        unknown = set(d) - ALLOWED
        if unknown:
            raise SystemExit(f"{f}: unknown keys {sorted(unknown)} (allowed: {sorted(ALLOWED)})")
        if d.get("name") != plugin_dir or not _NAME.match(plugin_dir):
            raise SystemExit(f"{f}: 'name' must equal the directory name {plugin_dir!r}")
        if not isinstance(d.get("description"), str) or not d["description"].strip():
            raise SystemExit(f"{f}: needs a non-empty 'description'")
        entries[plugin_dir] = d
    return entries


def entry_for(d: dict, ver: str) -> dict:
    out = {
        "name": d["name"],
        "source": f"./plugins/{d['name']}",
        "description": d["description"],
        "version": ver,
        "author": dict(OWNER),
        "repository": REPOSITORY,
        "license": LICENSE,
        "keywords": list(d.get("keywords", [])),
        "strict": bool(d.get("strict", False)),
    }
    if d.get("dependencies"):
        out["dependencies"] = list(d["dependencies"])
    return out


def build() -> dict:
    ver = version()
    return {
        "name": "consilience-ai2",
        "owner": dict(OWNER),
        "metadata": {"description": "Deterministic validity checks (evidence receipts, "
                                    "experiment audit, reproduction verdicts) for Claude Code"},
        "plugins": [entry_for(d, ver) for _, d in sorted(load_entries().items())],
    }


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def check(strict: bool) -> int:
    fresh = build()
    committed = json.loads(MARKETPLACE.read_text())
    ok = True
    fresh_by = {p["name"]: p for p in fresh["plugins"]}
    for p in committed.get("plugins", []):
        if p["name"] not in fresh_by:
            print(f"marketplace: lists {p['name']!r} but plugins/{p['name']}/{ENTRY} is missing")
            ok = False
        elif p != fresh_by[p["name"]]:
            print(f"marketplace: entry {p['name']!r} differs from its {ENTRY} (run make marketplace)")
            ok = False
    listed = {p["name"] for p in committed.get("plugins", [])}
    for name in sorted(set(fresh_by) - listed):
        msg = f"marketplace: plugin {name!r} is not listed yet (the integrator runs make marketplace)"
        if strict:
            print(msg)
            ok = False
        else:
            print("warning: " + msg)
    if strict and MARKETPLACE.read_text() != render(fresh):
        print("marketplace: .claude-plugin/marketplace.json is not a fresh build")
        ok = False
    if ok:
        print(f"marketplace: OK ({len(listed)} listed, {len(fresh_by)} entry files)")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        return check(a.strict)
    MARKETPLACE.parent.mkdir(parents=True, exist_ok=True)
    MARKETPLACE.write_text(render(build()))
    print(f"marketplace: wrote {MARKETPLACE.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
