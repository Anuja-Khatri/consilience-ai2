"""P1 commit order: were the thresholds committed before the result?

asta-flows: "Commit the test and its threshold, both significance and minimum effect,
before running anything." Two ways to show it, tried in this order:

1. **Declared commit refs** (``thresholds.committed.commit`` and
   ``result_committed.commit``) in a git repository (``--repo``, else the repository
   that holds the record). Both must resolve to commits. The thresholds commit must be
   a strict ancestor of the result commit (``git merge-base --is-ancestor``); commit
   order in the graph, not clock times, decides. Committer times and any declared times
   are reported beside it.
2. **The record file's own history** (``git log -- <record>``). Each committed version
   of the file is parsed. ``T`` is the first commit whose thresholds equal the current
   thresholds; ``R`` the first commit with any reproduction result number. Pass when
   ``T`` comes strictly before ``R`` and the thresholds never differ from the current
   ones in ``R`` or any later commit.

Outcomes: ``committed_first`` (pass); ``thresholds_post_hoc`` with a reason. Proven
post hoc (``same_commit``, ``after_result``, ``changed_after_result``) is an error.
When the order cannot be shown (no repository, refs that do not resolve, an untracked
record, a result or threshold never committed, unrelated histories) the outcome is
still ``thresholds_post_hoc`` (a threshold not shown to come first is not credited),
with reason ``not_shown`` and a warning, and the details say why. A record with no
result numbers is ``not_applicable``.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from consilience_ai2.reproduce.record import RecordError, parse_text

THRESHOLD_KEYS = ("alpha", "sides", "minimum_effect", "minimum_effect_scale",
                  "equivalence_margin", "power")
RESULT_KEYS = ("value", "p", "ci", "se", "effect_size", "n")


@dataclass
class CommitOrder:
    cls: str  # committed_first | thresholds_post_hoc | not_applicable
    reason: str | None = None
    method: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def proven(self) -> bool:
        return self.cls == "thresholds_post_hoc" and self.reason != "not_shown"


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           check=False, env=_ENV)
    except FileNotFoundError:
        return 127, "git not found"
    return p.returncode, p.stdout.strip() if p.returncode == 0 else p.stderr.strip()


# git output must not depend on the user's locale or pager settings
_ENV = {**os.environ, "GIT_PAGER": "cat", "LC_ALL": "C"}


def find_repo(start: Path) -> Path | None:
    code, out = _git(start if start.is_dir() else start.parent, "rev-parse",
                     "--show-toplevel")
    return Path(out) if code == 0 and out else None


def _commit(repo: Path, ref: str) -> tuple[str | None, int | None]:
    code, out = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if code != 0 or not out:
        return None, None
    code, t = _git(repo, "show", "-s", "--format=%ct", out)
    return out, int(t) if code == 0 and t.isdigit() else None


def _is_ancestor(repo: Path, a: str, b: str) -> bool:
    return _git(repo, "merge-base", "--is-ancestor", a, b)[0] == 0


def thresholds_signature(data: dict[str, Any]) -> dict[str, Any]:
    th = data.get("thresholds") or {}
    return {k: th.get(k) for k in THRESHOLD_KEYS}


def has_result(data: dict[str, Any]) -> bool:
    rep = data.get("reproduction") or {}
    return any(rep.get(k) is not None for k in RESULT_KEYS if k != "n")


def _not_shown(why: str, method: str | None, **det: Any) -> CommitOrder:
    return CommitOrder("thresholds_post_hoc", "not_shown", method, {"why": why, **det})


def check_commit_order(data: dict[str, Any], record_path: str | Path | None,
                       repo: str | Path | None = None) -> CommitOrder:
    if not has_result(data):
        return CommitOrder("not_applicable", "no result numbers in the record")
    tref = ((data.get("thresholds") or {}).get("committed") or {}).get("commit")
    rref = (data.get("result_committed") or {}).get("commit")
    rpath = Path(record_path).resolve() if record_path is not None else None
    root = Path(repo).resolve() if repo is not None else (
        find_repo(rpath) if rpath is not None else None)
    if root is None or find_repo(root) is None:
        return _not_shown("no git repository (give --repo)", None)
    root = find_repo(root) or root
    if tref and rref:
        return _by_refs(root, tref, rref, data)
    if rpath is None:
        return _not_shown("no commit refs declared and no record file to read the "
                          "history of", None)
    return _by_history(root, rpath, data)


def _by_refs(root: Path, tref: str, rref: str, data: dict[str, Any]) -> CommitOrder:
    method = "declared commit refs"
    t, tt = _commit(root, tref)
    r, rt = _commit(root, rref)
    det: dict[str, Any] = {"thresholds_commit": t, "result_commit": r,
                           "thresholds_commit_time": tt, "result_commit_time": rt,
                           "declared_thresholds_time":
                               ((data.get("thresholds") or {}).get("committed") or {}).get("time"),
                           "declared_result_time": (data.get("result_committed") or {}).get("time")}
    if t is None or r is None:
        missing = [n for n, c in (("thresholds", t), ("result", r)) if c is None]
        return _not_shown(f"commit not found: {', '.join(missing)}", method, **det)
    if t == r:
        return CommitOrder("thresholds_post_hoc", "same_commit", method, det)
    if _is_ancestor(root, t, r):
        return CommitOrder("committed_first", None, method, det)
    if _is_ancestor(root, r, t):
        return CommitOrder("thresholds_post_hoc", "after_result", method, det)
    return _not_shown("the two commits are on unrelated histories", method, **det)


def _by_history(root: Path, rpath: Path, data: dict[str, Any]) -> CommitOrder:
    method = "git log of the record file"
    try:
        rel = rpath.relative_to(root).as_posix()
    except ValueError:
        return _not_shown("the record is outside the repository", method)
    code, out = _git(root, "log", "--format=%H %ct", "--reverse", "--", rel)
    if code != 0 or not out:
        return _not_shown("the record file has no committed history", method, path=rel)
    current = thresholds_signature(data)
    first_t = first_r = None
    sigs: list[tuple[str, int, dict | None, bool]] = []
    unparsed = 0
    for line in out.splitlines():
        sha, ts = line.split()
        c, text = _git(root, "show", f"{sha}:{rel}")
        if c != 0:
            sigs.append((sha, int(ts), None, False))
            continue
        try:
            d = parse_text(text, f"{sha[:12]}:{rel}")
        except RecordError:
            unparsed += 1
            sigs.append((sha, int(ts), None, False))
            continue
        sigs.append((sha, int(ts), thresholds_signature(d), has_result(d)))
    for i, (_, _, sig, res) in enumerate(sigs):
        if first_t is None and sig == current:
            first_t = i
        if first_r is None and res:
            first_r = i
    det: dict[str, Any] = {"path": rel, "commits": len(sigs), "unparsed_versions": unparsed}
    if first_r is not None:
        det["result_commit"] = sigs[first_r][0]
        det["result_commit_time"] = sigs[first_r][1]
    if first_t is not None:
        det["thresholds_commit"] = sigs[first_t][0]
        det["thresholds_commit_time"] = sigs[first_t][1]
    if first_r is None:
        return _not_shown("the result is not committed", method, **det)
    if first_t is None:
        return _not_shown("the current thresholds are not committed", method, **det)
    if first_t == first_r:
        return CommitOrder("thresholds_post_hoc", "same_commit", method, det)
    if first_t > first_r:
        return CommitOrder("thresholds_post_hoc", "after_result", method, det)
    changed = [s[0] for s in sigs[first_r:] if s[2] is not None and s[2] != current]
    if changed:
        det["changed_in"] = changed
        return CommitOrder("thresholds_post_hoc", "changed_after_result", method, det)
    return CommitOrder("committed_first", None, method, det)
