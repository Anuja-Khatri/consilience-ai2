import hashlib

import pytest

from consilience_ai2.core.hashing import (
    canonical_json,
    sha256_bytes,
    sha256_file,
    sha256_json,
    sha256_text,
)


def test_bytes_and_text():
    assert sha256_bytes(b"") == hashlib.sha256(b"").hexdigest()
    assert sha256_text("é") == hashlib.sha256("é".encode()).hexdigest()


def test_file_matches_bytes(tmp_path):
    data = b"x" * (3 * 1024 * 1024 + 7)  # spans several read chunks
    p = tmp_path / "f.bin"
    p.write_bytes(data)
    assert sha256_file(p) == sha256_bytes(data)
    assert sha256_file(str(p)) == sha256_bytes(data)


def test_canonical_json_is_order_independent():
    a = {"b": 1, "a": [1, 2, {"y": "é", "x": None}]}
    b = {"a": [1, 2, {"x": None, "y": "é"}], "b": 1}
    assert canonical_json(a) == canonical_json(b) == '{"a":[1,2,{"x":null,"y":"é"}],"b":1}'
    assert sha256_json(a) == sha256_json(b)


def test_canonical_json_refuses_nan():
    with pytest.raises(ValueError):
        canonical_json({"v": float("nan")})
