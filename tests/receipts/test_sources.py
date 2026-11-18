"""E6 local source text: the Asta PaperStore adapter, a corpus_id-keyed text directory,
and several --sources tried in order. The PaperStore here is synthetic, written in the
layout asta-theorizer's ``PaperStore.save`` produces (pinned in the last test, which is
skipped when the pinned checkout is not in the local cache)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from consilience_ai2.cli import main
from consilience_ai2.fetch import FetchError, require
from consilience_ai2.receipts import check_workspace
from consilience_ai2.receipts.sources import ChainStore, PaperStoreStore, open_sources

MARKDOWN = ("# A study\n\nWe measured the effect in 40 sites. The effect is "
            "large and “robust” across sites.\n")


def paperstore() -> dict:
    """The layout PaperStore.save writes: primary keys in ``paperstore``, every alternate
    key (corpus_id, S2 sha, sanitised title) mapped to its primary key in the LUT."""
    return {
        "paperstore_lut": {
            "paper-1001": "paper-1001",
            "paper-abc123sha": "paper-1001",
            "paper-a_study": "paper-1001",
            "paper-1002": "paper-1002",
            "paper-1003": "paper-1003",
        },
        "paperstore": {
            "paper-1001": {"status": "full-text", "s2_id": "abc123sha", "corpus_id": "1001",
                           "title": "A study", "publication_year": 2024,
                           "publication_month": 5, "s2_metadata": {}, "paper_urls": [],
                           "paper_markdown": MARKDOWN},
            "paper-1002": {"status": "metadata-only", "corpus_id": "1002",
                           "paper_markdown": None},
            "paper-1003": {"status": "failed"},
            "paper-1004": {"status": "full-text", "corpus_id": "1004",
                           "paper_markdown": "Text kept only under its primary key."},
        },
    }


def workspace(root: Path, entries: dict[str, dict]) -> Path:
    lines = ["evidence:"]
    body = []
    for k, e in entries.items():
        lines.append(f"  {k}:")
        lines.append(f"    quote: {json.dumps(e['quote'])}")
        if "corpus_id" in e:
            lines += ["    provenance:", f"      corpus_id: {e['corpus_id']}"]
        if "cite" in e:
            lines.append(f"    cite: {e['cite']}")
        body.append(f'[claim {k}]{{.ev key="{k}"}}')
    root.mkdir(parents=True, exist_ok=True)
    (root / "evidence.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "index.qmd").write_text("\n\n".join(body) + "\n", encoding="utf-8")
    (root / "references.bib").write_text("@article{lee2023,\n title={x}\n}\n")
    return root


def e6(report) -> dict:
    return {f.key: f for f in report.findings if f.code == "E6"}


def test_paperstore_lookup_found_and_uncheckable(tmp_path):
    ps = tmp_path / "theory" / "paperstore.json"
    ps.parent.mkdir()
    ps.write_text(json.dumps(paperstore(), indent=4), encoding="utf-8")
    ws = workspace(tmp_path / "ws", {
        "found": {"quote": "The effect is large and \"robust\" across sites.", "corpus_id": 1001},
        "absent": {"quote": "The effect is small.", "corpus_id": 1001},
        "meta": {"quote": "x", "corpus_id": 1002},
        "failed": {"quote": "x", "corpus_id": 1003},
        "primary": {"quote": "kept only under its primary key", "corpus_id": 1004},
        "missing": {"quote": "x", "corpus_id": 9999},
        "nocid": {"quote": "x", "cite": "lee2023"},
    })
    out = e6(check_workspace(ws, ps))
    f = out["found"]
    assert f.details["outcome"] == "FOUND" and f.severity == "info"
    assert f.receipt.source == "paperstore:1001"
    assert f.receipt.sha256 == hashlib.sha256(MARKDOWN.encode("utf-8")).hexdigest()
    a, b = f.receipt.offset, f.receipt.end
    assert MARKDOWN[a:b] == "The effect is large and “robust” across sites."
    assert out["absent"].details["outcome"] == "NOT_FOUND" and out["absent"].severity == "error"
    assert "metadata-only" in out["meta"].message
    assert "failed" in out["failed"].message
    assert out["primary"].details["outcome"] == "FOUND"
    assert "not in the PaperStore" in out["missing"].message
    assert "corpus_id" in out["nocid"].message


def test_directory_keyed_by_corpus_id(tmp_path):
    src = tmp_path / "texts"
    src.mkdir()
    (src / "1001.txt").write_text("We measured the effect in 40 sites.", encoding="utf-8")
    (src / "lee2023.md").write_text("cite-keyed text", encoding="utf-8")
    ws = workspace(tmp_path / "ws", {
        "bycid": {"quote": "in 40 sites", "corpus_id": 1001},
        "bycite": {"quote": "cite-keyed", "cite": "lee2023", "corpus_id": 7},
    })
    out = e6(check_workspace(ws, src))
    assert out["bycid"].receipt.source == "file:1001.txt"
    assert out["bycite"].receipt.source == "file:lee2023.md"  # cite is tried first


def test_several_sources_are_tried_in_order(tmp_path):
    ps = tmp_path / "paperstore.json"
    ps.write_text(json.dumps(paperstore()), encoding="utf-8")
    src = tmp_path / "texts"
    src.mkdir()
    (src / "1002.txt").write_text("Text for the metadata-only paper.", encoding="utf-8")
    (src / "1001.txt").write_text("A different text for 1001.", encoding="utf-8")
    store = open_sources([ps, src])
    assert isinstance(store, ChainStore)
    assert store.describe()["stores"][0] == {"kind": "paperstore", "papers": 4}
    ws = workspace(tmp_path / "ws", {
        "a": {"quote": "in 40 sites", "corpus_id": 1001},
        "b": {"quote": "metadata-only paper", "corpus_id": 1002},
        "c": {"quote": "x", "corpus_id": 9999},
    })
    out = e6(check_workspace(ws, [ps, src]))
    assert out["a"].receipt.source == "paperstore:1001"  # the first store wins
    assert out["b"].receipt.source == "file:1002.txt"  # falls through to the directory
    assert out["c"].details["outcome"] == "UNCHECKABLE"
    assert "paperstore:" in out["c"].message and "directory:" in out["c"].message
    assert isinstance(open_sources([ps]), PaperStoreStore)


def test_cli_accepts_repeated_sources(tmp_path, capsys):
    ps = tmp_path / "paperstore.json"
    ps.write_text(json.dumps(paperstore()), encoding="utf-8")
    src = tmp_path / "texts"
    src.mkdir()
    (src / "1002.txt").write_text("Text for the metadata-only paper.", encoding="utf-8")
    ws = workspace(tmp_path / "ws", {
        "a": {"quote": "in 40 sites", "corpus_id": 1001},
        "b": {"quote": "metadata-only paper", "corpus_id": 1002},
    })
    out = tmp_path / "r.json"
    code = main(["receipts", "check", str(ws), "--sources", str(ps), "--sources", str(src),
                 "--json", str(out), "--no-annotations"])
    assert code == 0
    rep = json.loads(out.read_text())
    srcs = sorted(f["receipt"]["source"] for f in rep["findings"] if f["code"] == "E6")
    assert srcs == ["file:1002.txt", "paperstore:1001"]
    assert rep["sources"]["kind"] == "chain"


def test_paperstore_format_matches_the_pinned_upstream():
    try:
        root = require("asta-theorizer")
    except FetchError:
        pytest.skip("asta-theorizer is not in the local cache")
    src = (root / "src" / "PaperStore.py").read_text(encoding="utf-8")
    assert '"paperstore_lut": self.paperstore_lut,' in src
    assert '"paperstore": self.paperstore,' in src
    assert 'return "paper-" + corpus_id' in src
    assert '"paper_markdown": paper_markdown,' in src
    assert 'FULL_TEXT = "full-text"' in src and 'METADATA_ONLY = "metadata-only"' in src
