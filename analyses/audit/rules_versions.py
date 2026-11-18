"""Frozen rule versions of the audit, and how to run an analysis under one of them.

A published result stays reproducible after the rules change: the result of rules v0.1
(``audit-rules-1``) is recomputed from the exact rules it was scored with, taken from git
by tree id, not from the working copy. ``run_under(V01, "codescientist_heldout")`` builds
a throwaway copy of the package whose ``consilience_ai2/audit`` is that git tree (the rest
of the package is the current one, as when the v0.1 results were last regenerated), runs
the module's ``run()`` in a separate interpreter with that copy first on ``sys.path``, and
returns its ``(metrics, info)``. Nothing is written inside the repository.

When the working copy's rules already are that tree (and are clean), the module runs in
this interpreter instead.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RULES_DIR = "consilience_ai2/audit"
ENV_TREE = "CONSILIENCE_AI2_AUDIT_RULES_TREE"


@dataclass(frozen=True)
class RuleSet:
    name: str           # "v0.1", "v0.2"
    rules_version: str  # the RULES_VERSION string in the engine
    commit: str         # a commit whose consilience_ai2/audit is ``tree``
    tree: str           # git tree id of consilience_ai2/audit


V01 = RuleSet("v0.1", "audit-rules-1", "d24d2f7738496448b9c68fa529ce89cda7ce5c2d",
              "cca16a044d8074fd2672026af812a67dd6cafc31")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, check=False)


def working_tree() -> str | None:
    """Tree id of the committed ``consilience_ai2/audit`` at HEAD, or None when git is
    unavailable or that directory has uncommitted changes. Inside ``run_under`` it is the
    tree the frozen copy was built from."""
    env = os.environ.get(ENV_TREE)
    if env:
        return env
    try:
        dirty = _git("status", "--porcelain", "--", RULES_DIR)
        if dirty.returncode != 0 or dirty.stdout.strip():
            return None
        out = _git("rev-parse", f"HEAD:{RULES_DIR}")
        return out.stdout.decode().strip() or None
    except OSError:
        return None


def _materialise(rs: RuleSet, dest: Path) -> None:
    got = _git("rev-parse", f"{rs.commit}:{RULES_DIR}").stdout.decode().strip()
    if got != rs.tree:
        raise RuntimeError(f"rules {rs.name}: {rs.commit}:{RULES_DIR} is {got!r}, "
                           f"expected {rs.tree}")
    pkg = dest / "consilience_ai2"
    shutil.copytree(REPO / "consilience_ai2", pkg,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.rmtree(pkg / "audit")
    tar = _git("archive", "--format=tar", rs.tree)
    if tar.returncode != 0:
        raise RuntimeError(f"git archive {rs.tree} failed: {tar.stderr.decode()}")
    (pkg / "audit").mkdir()
    subprocess.run(["tar", "-x", "-C", str(pkg / "audit")], input=tar.stdout, check=True)


_RUNNER = """
import json, sys
sys.path.insert(0, sys.argv[1])
import importlib
import consilience_ai2.audit as a
assert a.__file__.startswith(sys.argv[2]), a.__file__
mod = importlib.import_module(sys.argv[3])
ms, info = getattr(mod, sys.argv[4])()
with open(sys.argv[5], "w", encoding="utf-8") as fh:
    json.dump({"metrics": ms, "info": info, "rules_version": a.RULES_VERSION}, fh,
              sort_keys=True, allow_nan=False)
"""


def run_under(rs: RuleSet, module: str, func: str = "run") -> tuple[list[dict], dict]:
    """``module.func()`` with the audit rules of ``rs``; returns ``(metrics, info)``."""
    if working_tree() == rs.tree:
        import importlib
        return getattr(importlib.import_module(module), func)()
    with tempfile.TemporaryDirectory(prefix="consilience-audit-rules-") as tmp:
        root = Path(tmp)
        _materialise(rs, root / "pkg")
        out = root / "out.json"
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(root / "pkg"), str(HERE)])
        env[ENV_TREE] = rs.tree
        subprocess.run([sys.executable, "-c", _RUNNER, str(HERE), str(root / "pkg"), module,
                        func, str(out)], env=env, check=True, cwd=str(root))
        got = json.loads(out.read_text(encoding="utf-8"))
    if got["rules_version"] != rs.rules_version:
        raise RuntimeError(f"rules {rs.name}: ran {got['rules_version']}")
    return got["metrics"], got["info"]
