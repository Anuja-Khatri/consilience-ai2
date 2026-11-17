#!/usr/bin/env python3
"""Tracked-tree guard: secrets, downloaded data and model identifiers.

Pattern from lab-gate (eval/check_secrets.py). It scans every git-tracked file and
fails (exit 1) on:

1. key-SHAPED secrets: the full shape (prefix + long tail), never a bare prefix, so
   prose that names a pattern does not trip;
2. data that must never be committed: files named like the CodeScientist API-key file,
   ``.env`` files, archives (``.zip``, ``.tar.gz``, ``.parquet``), the downloaded source
   files by name, and any tracked file larger than 2 MB;
3. AI model identifiers (versioned model names). This repository describes tools and
   data, not which model produced them.

Matched VALUES are never printed: only file:line and the pattern name. A line that must
name a pattern can be exempted in ``scripts/secrets_allowlist.txt`` (a substring per
line). This file itself is skipped.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALLOWLIST = REPO / "scripts" / "secrets_allowlist.txt"
SELF = Path(__file__).resolve()
MAX_BYTES = 2 * 1024 * 1024

SECRETS = [
    ("api key sk-", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}")),
    ("google AIza", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
    ("github token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("huggingface token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("groq key", re.compile(r"\bgsk_[A-Za-z0-9]{30,}")),
]

MODEL_IDS = [
    ("model id", re.compile(r"\bclaude-(?:opus|sonnet|haiku|instant|\d)[\w.\-]*", re.I)),
    ("model id", re.compile(r"\b(?:sonnet|haiku|opus)[ \-_]?\d", re.I)),
    ("model id", re.compile(r"\bgpt-?(?:3\.5|4o?|4\.\d|5)(?![\w])[\w.\-]*", re.I)),
    ("model id", re.compile(r"\bo[134]-(?:mini|preview|high|pro)\b", re.I)),
    ("model id", re.compile(r"\bgemini-(?:\d|pro|flash|ultra)[\w.\-]*", re.I)),
    ("model id", re.compile(r"\b(?:llama|mistral|mixtral|qwen)-?\d[\w.\-]*", re.I)),
]

BAD_NAMES = [
    ("api key file", re.compile(r"(?:^|/)api_keys[^/]*\.json$")),
    ("env file", re.compile(r"(?:^|/)\.env(?:\.[^/]*)?$")),
    ("archive", re.compile(r"\.(?:zip|tar\.gz|tgz|parquet|7z)$", re.I)),
    ("downloaded source", re.compile(r"(?:^|/)(?:SciArena-Eval_train\.json|theorizer_paper_data\.zip|full50\.zip|example_experiments\.zip)$")),
]
NAME_OK = {".env.example"}


def load_allow() -> list[str]:
    if not ALLOWLIST.exists():
        return []
    return [ln.strip() for ln in ALLOWLIST.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True,
                             check=True).stdout.decode()
        return [REPO / f for f in out.split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in REPO.rglob("*") if ".git" not in p.parts and ".venv" not in p.parts]


def main() -> int:
    allow = load_allow()
    hits: list[tuple[str, int, str]] = []
    for p in tracked_files():
        if not p.is_file() or p.resolve() == SELF:
            continue
        rel = p.relative_to(REPO).as_posix()
        if Path(rel).name not in NAME_OK:
            for name, rx in BAD_NAMES:
                if rx.search(rel):
                    hits.append((rel, 0, name))
        if p.stat().st_size > MAX_BYTES:
            hits.append((rel, 0, f"file larger than {MAX_BYTES} bytes (data?)"))
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if any(a in line for a in allow):
                continue
            for name, rx in SECRETS + MODEL_IDS:
                if rx.search(line):
                    hits.append((rel, i, name))
    if hits:
        print("check_secrets: FAILED (values not shown):")
        for rel, i, name in hits:
            print(f"  {rel}:{i}  [{name}]")
        return 1
    print("check_secrets: clean (no secret, data file or model identifier in the tracked tree).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
