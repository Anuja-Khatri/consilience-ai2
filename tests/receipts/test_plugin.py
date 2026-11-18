"""The consilience-receipts plugin layout and its make-check snippet."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "consilience-receipts"
SKILL = PLUGIN / "skills" / "evidence-receipts"
SNIPPET = SKILL / "assets" / "evidence-receipts.mk"
NAME = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def test_marketplace_entry():
    d = json.loads((PLUGIN / "marketplace-entry.json").read_text())
    assert d["name"] == "consilience-receipts"
    assert set(d) <= {"name", "description", "keywords", "dependencies", "strict"}
    assert d["description"] and all(isinstance(k, str) for k in d["keywords"])
    assert not list(PLUGIN.rglob("plugin.json"))


def test_skill_frontmatter_in_asta_plugins_format():
    raw = (SKILL / "SKILL.md").read_text()
    assert raw.startswith("---\n")
    end = raw.index("\n---\n", 4)
    fm = yaml.safe_load(raw[4:end])
    assert fm["name"] == "evidence-receipts" == SKILL.name
    assert NAME.match(fm["name"]) and len(fm["name"]) <= 64
    assert isinstance(fm["description"], str) and 0 < len(fm["description"]) <= 1024
    assert isinstance(fm["allowed-tools"], str)  # space-separated, not a YAML list
    assert "Bash(consilience-ai2 receipts check *)" in fm["allowed-tools"]
    assert set(fm) == {"name", "description", "allowed-tools"}


def test_skill_names_every_code():
    body = (SKILL / "SKILL.md").read_text()
    for code in ("E0", "E1", "E2", "E3", "E4", "E5", "E6", "W1", "W2"):
        assert f"| {code} |" in body


def _make(ws, *extra):
    if shutil.which("make") is None:
        pytest.skip("make is not installed")
    cmd = f"{sys.executable} -m consilience_ai2"
    return subprocess.run(
        ["make", "-C", str(ws), "check", f"CONSILIENCE_AI2={cmd}", *extra],
        capture_output=True, text=True, timeout=120)


def _project(copy_example, src):
    ws = copy_example(src)
    shutil.copy(SNIPPET, ws / "evidence-receipts.mk")
    (ws / "Makefile").write_text(
        "# a project Makefile with its own check, as in an Asta workspace\n"
        ".PHONY: check\ncheck:\n\t@echo project checks ran\n\ninclude evidence-receipts.mk\n")
    return ws


def test_snippet_passes_on_clean_workspace(clean, copy_example):
    ws = _project(copy_example, clean)
    r = _make(ws, "RECEIPTS_SOURCES=sources")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "project checks ran" in r.stdout
    rep = json.loads((ws / "_receipts" / "receipts.json").read_text())
    assert rep["summary"]["by_severity"] == {"error": 0, "warning": 0, "info": 2}
    assert {f["details"]["outcome"] for f in rep["findings"]} == {"FOUND"}


def test_snippet_fails_make_check_on_seeded_workspace(seeded, copy_example):
    ws = _project(copy_example, seeded)
    r = _make(ws, "RECEIPTS_SOURCES=sources", "RECEIPTS_REPORT=out/r.json")
    assert r.returncode != 0
    assert "::error file=defects.qmd,line=7::E1" in r.stdout
    rep = json.loads((ws / "out" / "r.json").read_text())
    assert rep["summary"]["by_severity"]["error"] == 14


def test_snippet_fail_on_warnings(make_ws, copy_example, tmp_path):
    ws = make_ws({"evidence.yml": 'evidence:\n  k:\n    quote: "it may help"\n',
                  "index.qmd": '[It proves this]{.ev key="k"}\n'})
    shutil.copy(SNIPPET, ws / "evidence-receipts.mk")
    (ws / "Makefile").write_text("include evidence-receipts.mk\n")
    assert _make(ws).returncode == 0
    # the only defect is a W2, which is opt-in
    assert _make(ws, "RECEIPTS_FLAGS=--fail-on-warnings").returncode == 0
    assert _make(ws, "RECEIPTS_FLAGS=--with-w2 --fail-on-warnings").returncode != 0
    (ws / "index.qmd").write_text('[It helps 3 times]{.ev key="k"}\n')  # a W1
    assert _make(ws, "RECEIPTS_FLAGS=--fail-on-warnings").returncode != 0
