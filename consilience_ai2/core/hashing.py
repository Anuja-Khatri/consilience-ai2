"""SHA-256 of bytes, text, files and canonical JSON.

Every receipt in this package names a source by one of these hashes, so the functions
are small, pure and stable:

- ``sha256_bytes(b)``: the hex digest of raw bytes.
- ``sha256_text(s)``: the digest of ``s`` encoded as UTF-8 (no normalisation).
- ``sha256_file(path)``: the digest of a file's bytes, read in chunks.
- ``canonical_json(obj)``: one fixed serialisation (sorted keys, no whitespace,
  UTF-8, finite numbers only), so equal data gives equal bytes.
- ``sha256_json(obj)``: the digest of ``canonical_json(obj)``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CHUNK = 1 << 20


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Hex SHA-256 of ``text`` encoded as UTF-8. The text is not normalised."""
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str | Path) -> str:
    """Hex SHA-256 of the bytes of the file at ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def canonical_json(obj: Any) -> str:
    """The canonical JSON text of ``obj``: sorted keys, compact separators, UTF-8 kept.

    NaN and infinities are refused (``ValueError``): they have no JSON form, and a
    receipt over a value that cannot be written is not a receipt.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def sha256_json(obj: Any) -> str:
    """Hex SHA-256 of ``canonical_json(obj)``."""
    return sha256_text(canonical_json(obj))
