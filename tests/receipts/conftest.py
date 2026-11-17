"""Fixtures for the evidence-receipts tests. No network, no fetched data."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples" / "receipts"


@pytest.fixture
def seeded() -> Path:
    return EXAMPLES / "seeded"


@pytest.fixture
def clean() -> Path:
    return EXAMPLES / "clean"


@pytest.fixture
def make_ws(tmp_path):
    """Build a workspace from {relative path: text}; returns its root."""

    def build(files: dict[str, str], name: str = "ws") -> Path:
        root = tmp_path / name
        n = 1
        while root.exists():  # every call gets a fresh directory
            n += 1
            root = tmp_path / f"{name}{n}"
        for rel, text in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        root.mkdir(parents=True, exist_ok=True)
        return root

    return build


@pytest.fixture
def copy_example(tmp_path):
    def copy(src: Path) -> Path:
        dst = tmp_path / src.name
        shutil.copytree(src, dst)
        return dst

    return copy
