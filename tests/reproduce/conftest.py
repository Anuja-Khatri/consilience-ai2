"""Fixtures for the reproduction-verdict tests: a valid base record and a scratch git
repository. No network; every git call is local and fully configured here."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

BASE: dict[str, Any] = {
    "schema_version": 1,
    "id": "H1",
    "hypothesis": "Longer sleep is associated with better recall.",
    "source_hypothesis": "Longer sleep is associated with better recall.",
    "source": {
        "quantity": "Pearson r between sleep and recall",
        "value": 0.31, "unit": "dimensionless", "n": 240,
        "effect_size": {"type": "r", "value": 0.31}, "p": 0.000001,
        "conditions": {"cohort": "A", "method": "Pearson"},
    },
    "reproduction": {
        "quantity": "Pearson r between sleep and recall",
        "value": 0.27, "unit": "dimensionless", "n": 180,
        "effect_size": {"type": "r", "value": 0.27}, "p": 0.0002,
        "conditions": {"cohort": "B", "method": "Pearson"},
    },
    "quantity_mapping": {"relation": "same_quantity"},
    "independence_axis": "cohort",
    "thresholds": {"alpha": 0.05, "sides": 2, "minimum_effect": 0.1},
    "positive_control": {"p": 0.001},
}


def merge(base: dict, over: dict) -> dict:
    """Deep merge; a value of ``DELETE`` removes the key."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if v is DELETE:
            out.pop(k, None)
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


DELETE = object()


@pytest.fixture
def record():
    """``record(**overrides)`` -> a record dict (deep-merged onto a valid base)."""

    def make(over: dict | None = None, **kw: Any) -> dict:
        return merge(BASE, {**(over or {}), **kw})

    return make


@pytest.fixture
def delete():
    return DELETE


class Git:
    """A scratch repository with fixed identities and commit dates."""

    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.t = 1_700_000_000
        self.run("init", "-q")
        self.run("config", "user.email", "test@example.invalid")
        self.run("config", "user.name", "Test")
        self.run("config", "commit.gpgsign", "false")

    def run(self, *args: str, env: dict | None = None) -> str:
        p = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True,
                           text=True, check=True, env=env)
        return p.stdout.strip()

    def write(self, rel: str, data: dict) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
        return p

    def commit(self, msg: str, *paths: str) -> str:
        import os

        self.t += 60
        stamp = f"{self.t} +0000"
        env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        self.run("add", *(paths or ("-A",)))
        self.run("commit", "-q", "--allow-empty", "-m", msg, env=env)
        return self.run("rev-parse", "HEAD")


@pytest.fixture
def git_repo(tmp_path):
    return Git(tmp_path / "repo")


@pytest.fixture
def examples_dir(repo_root) -> Path:
    return repo_root / "examples" / "reproduce"
