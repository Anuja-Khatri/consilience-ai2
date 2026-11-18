"""Demo: the workflow P1 credits. The thresholds are committed BEFORE the result.

    python examples/reproduce/demo_commit_order.py [--keep DIR]

It builds a temporary git repository (deleted afterwards unless ``--keep`` names a new
directory) and replays a reproduction in two commits, as a real run should:

1. ``plan``: the record with the test, the source numbers, the reproduction's quantity,
   conditions and planned n, and the thresholds, but no reproduction result;
2. ``result``: the same record with the reproduction's numbers added. The thresholds
   are unchanged.

Then it runs ``consilience-ai2 reproduce check`` on the record. P1 reads the record's
own git history and finds the thresholds in a commit strictly before the first commit
with a result: ``committed_first``. The check exits 0. The record is
``examples/reproduce/records/committed_first.yaml``; checked in place, in this repository,
it fails P1 (``same_commit``), because there the plan and the result arrive in one commit.

Deterministic: fixed commit identity and dates, the fallback comparability backend.
Nothing is written to your git configuration.
"""

from __future__ import annotations

import argparse
import copy
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
RECORD = HERE / "records" / "committed_first.yaml"
REL = "reproduction/committed_first.yaml"
RESULT_FIELDS = ("value", "p", "ci", "ci_level", "se", "effect_size")
IDENTITY = ("-c", "user.name=Demo", "-c", "user.email=demo@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main")


def git(repo: Path, *args: str, when: int | None = None) -> str:
    env = {**os.environ, "LC_ALL": "C", "GIT_PAGER": "cat"}
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{when} +0000"
    p = subprocess.run(["git", *IDENTITY, "-C", str(repo), *args], capture_output=True,
                       text=True, check=True, env=env)
    return p.stdout.strip()


def plan_stage(record: dict) -> dict:
    """The record as committed before the run: no reproduction result, no prose verdict."""
    plan = copy.deepcopy(record)
    for k in RESULT_FIELDS:
        plan["reproduction"].pop(k, None)
    plan.pop("reported_verdict", None)
    return plan


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")


def build(repo: Path) -> Path:
    """Two commits in a fresh repository; returns the record's path."""
    full = yaml.safe_load(RECORD.read_text(encoding="utf-8"))
    git(repo, "init", "-q")
    rec = repo / REL
    write(rec, plan_stage(full))
    git(repo, "add", REL)
    git(repo, "commit", "-q", "-m", "plan: test and thresholds, before the run",
        when=1_700_000_000)
    write(rec, full)
    git(repo, "add", REL)
    git(repo, "commit", "-q", "-m", "result: reproduction numbers", when=1_700_003_600)
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keep", metavar="DIR", help="build the repository here and keep it "
                                                  "(the directory must not exist)")
    a = ap.parse_args(argv)
    if a.keep:
        repo = Path(a.keep)
        repo.mkdir(parents=True)
    else:
        repo = Path(tempfile.mkdtemp(prefix="c3-demo-"))
    try:
        rec = build(repo)
        print(git(repo, "log", "--format=%h %s", "--reverse"))
        cmd = [sys.executable, "-m", "consilience_ai2", "reproduce", "check", str(rec),
               "--repo", str(repo), "--backend", "fallback",
               "--json", str(repo / "reproduction_verdict.json")]
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        sys.stdout.write(p.stdout.replace(str(repo) + os.sep, ""))
        sys.stderr.write(p.stderr)
        print(f"exit {p.returncode}")
        return p.returncode
    finally:
        if not a.keep:
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
