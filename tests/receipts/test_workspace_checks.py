"""Each workspace check in both directions, on small temporary workspaces."""

from __future__ import annotations

import json

import pytest

from consilience_ai2.receipts import check_workspace
from consilience_ai2.receipts.sources import SourceError, open_sources
from consilience_ai2.receipts.workspace import asta_methods, bib_keys, valid_iso_date

QUARTO = "bibliography: references.bib\nmetadata-files:\n  - evidence.yml\n"
BIB = "@article{good2020,\n  title = {T},\n}\n@string{x = {y}}\n@comment{bad2020,}\n"


def codes(report, severity=None):
    return sorted((f.code, f.line, f.key) for f in report.findings
                  if severity is None or f.severity == severity)


def ws(make_ws, evidence: str, qmd: str, **extra) -> object:
    files = {"_quarto.yml": QUARTO, "references.bib": BIB, "evidence.yml": evidence,
             "index.qmd": qmd}
    files.update(extra)
    return make_ws(files)


ENTRY = 'evidence:\n  k:\n    quote: "a quote"\n    cite: good2020\n'


def test_clean_minimal(make_ws):
    r = check_workspace(ws(make_ws, ENTRY, '[claim]{.ev key="k"}\n'))
    assert codes(r, "error") == [] and codes(r, "warning") == []
    assert [f.details["outcome"] for f in r.findings] == ["UNCHECKABLE"]


# ---- E1


def test_e1_unknown_key(make_ws):
    r = check_workspace(ws(make_ws, ENTRY, '[claim]{.ev key="k"}\n[x]{.ev key="nope" quote="q"}\n'))
    assert ("E1", 2, "nope") in codes(r) and ("E2", 2, "nope") not in codes(r)


def test_e1_not_raised_for_known_key_or_no_key(make_ws):
    r = check_workspace(ws(make_ws, ENTRY, '[claim]{.ev key="k"}\n[x]{.ev quote="q"}\n'))
    assert not [c for c in codes(r) if c[0] == "E1"]


def test_e1_store_must_be_wired_in_quarto(make_ws):
    # evidence.yml exists but _quarto.yml does not list it: the filter would not see it
    root = make_ws({"_quarto.yml": "bibliography: references.bib\n", "references.bib": BIB,
                    "evidence.yml": ENTRY, "index.qmd": '[c]{.ev key="k"}\n'})
    assert ("E1", 1, "k") in codes(check_workspace(root))


def test_e1_non_map_entry_is_not_stored(make_ws):
    r = check_workspace(ws(make_ws, ENTRY + '  s: "just a string"\n',
                           '[a]{.ev key="k"}\n[b]{.ev key="s"}\n'))
    assert ("E1", 2, "s") in codes(r)


# ---- E2


def test_e2_no_quote_anywhere(make_ws):
    ev = ENTRY + '  empty:\n    quote: ""\n    cite: good2020\n  noq:\n    cite: good2020\n'
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n[b]{.ev key="empty"}\n'
                           '[c]{.ev key="noq"}\n[d]{.ev cite="good2020"}\n[e]{.ev key="gone"}\n'))
    e2 = [c for c in codes(r) if c[0] == "E2"]
    assert e2 == [("E2", 2, "empty"), ("E2", 3, "noq"), ("E2", 4, None), ("E2", 5, "gone")]


def test_e2_inline_quote_overrides_missing_stored_quote(make_ws):
    ev = ENTRY + '  noq:\n    cite: good2020\n'
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n[b]{.ev key="noq" quote="here"}\n'))
    assert not [c for c in codes(r) if c[0] == "E2"]


def test_e2_non_text_quote_is_not_a_quote(make_ws):
    ev = ENTRY + '  lst:\n    quote: [a, b]\n'
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n[b]{.ev key="lst"}\n'))
    assert ("E2", 2, "lst") in codes(r)


# ---- E3


def test_e3_stored_and_inline_cite(make_ws):
    ev = ENTRY + '  bad:\n    quote: "q"\n    cite: bad2020\n'
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n[b]{.ev key="bad"}\n'
                           '[c]{.ev quote="q" cite="ghost"}\n[d]{.ev quote="q" cite="good2020"}\n'))
    e3 = [(f.file, f.line, f.details["cite"]) for f in r.sorted_findings() if f.code == "E3"]
    assert e3 == [("evidence.yml", 7, "bad2020"), ("index.qmd", 3, "ghost")]


def test_e3_string_and_comment_are_not_entries():
    assert bib_keys(BIB) == {"good2020"}
    assert bib_keys("@Book ( key-1 ,\n title={x})\n@misc{k:2, }") == {"key-1", "k:2"}


def test_e3_inline_cite_overrides_stored_cite(make_ws):
    ev = 'evidence:\n  k:\n    quote: "a quote"\n    cite: good2020\n'
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k" cite="ghost"}\n'))
    assert [(f.file, f.line) for f in r.findings if f.code == "E3"] == [("index.qmd", 1)]


def test_e3_front_matter_bibliography(make_ws):
    files = {
        "_quarto.yml": "metadata-files: [evidence.yml]\n",
        "evidence.yml": ENTRY,
        "index.qmd": '---\nbibliography: local.bib\n---\n[a]{.ev key="k"}\n',
        "local.bib": "@misc{good2020,}\n",
    }
    # the entry's cite resolves in the bibliography of the document that uses it
    assert not [f for f in check_workspace(make_ws(files)).findings if f.code == "E3"]
    # but not when no document using it has that bibliography
    files["other.qmd"] = '[b]{.ev quote="q" cite="good2020"}\n'
    files["index.qmd"] = '[a]{.ev key="k"}\n'
    got = [(f.file, f.line) for f in check_workspace(make_ws(files)).sorted_findings()
           if f.code == "E3"]
    assert got == [("evidence.yml", 4), ("other.qmd", 1)]


# ---- E4


def test_e4_orphan_and_used(make_ws):
    ev = ENTRY + '  orphan:\n    quote: "q"\n    cite: good2020\n'
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n'))
    assert [(c[0], c[1], c[2]) for c in codes(r) if c[0] == "E4"] == [("E4", 5, "orphan")]
    r2 = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n[b]{.ev key="orphan"}\n'))
    assert not [c for c in codes(r2) if c[0] == "E4"]


def test_e4_counts_spans_in_any_file_but_not_in_code(make_ws):
    ev = ENTRY + '  other:\n    quote: "q"\n'
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n`[b]{.ev key="other"}`\n',
                           **{"sub/page.qmd": '[c]{.ev key="other"}\n'}))
    assert not [c for c in codes(r) if c[0] == "E4"]
    r2 = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n`[b]{.ev key="other"}`\n'))
    assert ("E4", 5, "other") in codes(r2)


def test_skipped_directories(make_ws):
    r = check_workspace(ws(make_ws, ENTRY, '[a]{.ev key="k"}\n', **{
        "_extensions/x/page.qmd": '[b]{.ev key="nope1"}\n',
        ".quarto/page.qmd": '[b]{.ev key="nope2"}\n',
        "_site/page.qmd": '[b]{.ev key="nope3"}\n',
        "node_modules/page.qmd": '[b]{.ev key="nope4"}\n',
        "_include.qmd": '[b]{.ev key="k"}\n'}))
    assert not [c for c in codes(r) if c[0] == "E1"]
    assert r.extra["checked_spans"] == 2


# ---- E5


def prov(**fields) -> str:
    lines = "".join(f"      {k}: {v}\n" for k, v in fields.items())
    return f'evidence:\n  k:\n    quote: "q"\n    cite: good2020\n    provenance:\n{lines}'


def e5(make_ws, ev):
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="k"}\n'))
    return sorted((f.details["field"], f.line) for f in r.findings if f.code == "E5")


def test_e5_valid_provenance(make_ws):
    assert e5(make_ws, prov(method="asta papers snippet-search", query='"x y"',
                            corpus_id=289622360, url="https://x.org/a", retrieved="2026-08-29",
                            note='"n"')) == []
    assert e5(make_ws, prov(url="asta://documents/abc", method="asta documents")) == []
    assert e5(make_ws, prov(url="HTTP://X.ORG", method="asta generate-theories run")) == []
    assert e5(make_ws, prov(corpus_id="'12'")) == []


def test_e5_each_field_flagged(make_ws):
    assert e5(make_ws, prov(method="asta search papers")) == [("method", 6)]
    assert e5(make_ws, prov(method='"asta papers snippet-search -q x"')) == [("method", 6)]
    assert e5(make_ws, prov(method='"asta documents --all"')) == [("method", 6)]
    assert e5(make_ws, prov(method='"asta papers snippet-search "')) == [("method", 6)]
    assert e5(make_ws, prov(method="snippet-search")) == [("method", 6)]
    assert e5(make_ws, prov(corpus_id="12a")) == [("corpus_id", 6)]
    assert e5(make_ws, prov(corpus_id="-5")) == [("corpus_id", 6)]
    assert e5(make_ws, prov(corpus_id="1.5")) == [("corpus_id", 6)]
    assert e5(make_ws, prov(url="ftp://x")) == [("url", 6)]
    assert e5(make_ws, prov(url="javascript:alert(1)")) == [("url", 6)]
    assert e5(make_ws, prov(url="www.example.org")) == [("url", 6)]
    assert e5(make_ws, prov(retrieved="2026-02-30")) == [("retrieved", 6)]
    assert e5(make_ws, prov(retrieved="29/08/2026")) == [("retrieved", 6)]
    assert e5(make_ws, prov(retrieved="2026-08-29T10:00:00")) == [("retrieved", 6)]


def test_e5_provenance_not_a_map(make_ws):
    ev = 'evidence:\n  k:\n    quote: "q"\n    provenance: [a, b]\n'
    assert e5(make_ws, ev) == [("provenance", 4)]


def test_methods_list_and_dates():
    m = asta_methods()
    assert m.accepts("asta papers snippet-search") and not m.accepts("asta papers")
    assert m.accepts("asta documents") and m.accepts("asta documents add")
    assert not m.accepts("asta documents Add")
    assert valid_iso_date("2024-02-29") and not valid_iso_date("2023-02-29")


# ---- E6


def test_e6_found_not_found_uncheckable_with_directory(make_ws, tmp_path):
    ev = (ENTRY + '  miss:\n    quote: "never said"\n    cite: good2020\n'
          '  byid:\n    quote: "second  line"\n    provenance:\n      corpus_id: 42\n'
          '  nokey:\n    quote: "x"\n    source: "free text"\n')
    root = ws(make_ws, ev, '[a]{.ev key="k"}\n[b]{.ev key="miss"}\n[c]{.ev key="byid"}\n'
              '[d]{.ev key="nokey"}\n[e]{.ev quote="a quote" cite="unknown2"}\n')
    src = tmp_path / "src"
    src.mkdir()
    (src / "good2020.txt").write_text("Here is a quote, in full.")
    (src / "42.md").write_text("first line\nsecond\n  line\n")
    r = check_workspace(root, src)
    out = {f.line: (f.severity, f.details["outcome"]) for f in r.findings if f.code == "E6"}
    assert out == {1: ("info", "FOUND"), 2: ("error", "NOT_FOUND"), 3: ("info", "FOUND"),
                   4: ("info", "UNCHECKABLE"), 5: ("info", "UNCHECKABLE")}
    f1 = next(f for f in r.findings if f.code == "E6" and f.line == 1)
    assert (f1.receipt.offset, f1.receipt.end) == (8, 15)
    assert f1.receipt.source == "file:good2020.txt"
    assert r.exit_code() == 1


def test_e6_paperstore(make_ws, tmp_path):
    store = {"paperstore_lut": {"paper-7": "paper-abc", "paper-8": "paper-8"},
             "paperstore": {"paper-abc": {"status": "full-text", "corpus_id": "7",
                                          "paper_markdown": "Full text with the quote here."},
                            "paper-8": {"status": "metadata-only", "paper_markdown": None}}}
    ps = tmp_path / "paperstore.json"
    ps.write_text(json.dumps(store))
    ev = ('evidence:\n  a:\n    quote: "the quote"\n    provenance:\n      corpus_id: 7\n'
          '  b:\n    quote: "x"\n    provenance:\n      corpus_id: 8\n'
          '  c:\n    quote: "x"\n    provenance:\n      corpus_id: 9\n'
          '  d:\n    quote: "x"\n    cite: good2020\n')
    root = ws(make_ws, ev, '[a]{.ev key="a"}\n[b]{.ev key="b"}\n[c]{.ev key="c"}\n[d]{.ev key="d"}\n')
    r = check_workspace(root, ps)
    out = {f.key: f for f in r.findings if f.code == "E6"}
    assert out["a"].details["outcome"] == "FOUND"
    assert out["a"].receipt.source == "paperstore:7"
    assert "metadata-only" in out["b"].message
    assert "not in the PaperStore" in out["c"].message
    assert "corpus_id" in out["d"].message


def test_e6_autodiscovery_index(make_ws, tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"experiments": [
        {"experiment": 3, "hypothesis": "H.", "analysis": "The rate rose by 4%.",
         "review": "", "link": ""}]}))
    ev = ('evidence:\n  a:\n    quote: "The rate rose by 4%."\n    source: "AutoDiscovery run r1, experiment 3"\n'
          '  b:\n    quote: "x"\n    source: "AutoDiscovery run r1, experiment 4"\n')
    r = check_workspace(ws(make_ws, ev, '[a]{.ev key="a"}\n[b]{.ev key="b"}\n'), idx)
    out = {f.key: f.details["outcome"] for f in r.findings if f.code == "E6"}
    assert out == {"a": "FOUND", "b": "UNCHECKABLE"}


def test_open_sources_errors(tmp_path):
    with pytest.raises(SourceError):
        open_sources(tmp_path / "missing")
    bad = tmp_path / "x.json"
    bad.write_text("[1]")
    with pytest.raises(SourceError):
        open_sources(bad)
    bad.write_text("{not json")
    with pytest.raises(SourceError):
        open_sources(bad)


# ---- W1 / W2 through the workspace


def test_w1_w2_in_workspace_both_directions(make_ws):
    ev = ('evidence:\n  a:\n    quote: "accuracy of 87.5% may be associated with size"\n'
          '    cite: good2020\n')
    root = ws(make_ws, ev, '[accuracy of 87.5%]{.ev key="a"}\n'
                       '[accuracy of 90%]{.ev key="a"}\n[size causes accuracy]{.ev key="a"}\n'
                       '[size may affect accuracy]{.ev key="a"}\n')
    r = check_workspace(root, with_w2=True)
    assert [(f.code, f.line) for f in r.findings if f.severity == "warning"] == [
        ("W1", 2), ("W2", 3)]
    default = check_workspace(root)  # W2 is opt-in
    assert [(f.code, f.line) for f in default.findings if f.severity == "warning"] == [
        ("W1", 2)]
    w1 = next(f for f in r.findings if f.code == "W1")
    assert w1.receipt.source == "evidence:a" and w1.details["unsupported"] == ["90%"]
    assert r.exit_code() == 0


# ---- E0 and store layout


def test_e0_bad_yaml_and_missing_files(make_ws):
    root = make_ws({"_quarto.yml": "metadata-files: [evidence.yml, gone.yml]\nbibliography: nope.bib\n",
                    "evidence.yml": "evidence: [unclosed\n", "index.qmd": "text\n"})
    r = check_workspace(root)
    sev = sorted((f.severity, f.file) for f in r.findings if f.code == "E0")
    assert sev == [("error", "evidence.yml"), ("warning", "_quarto.yml"), ("warning", "_quarto.yml")]
    assert r.exit_code() == 1


def test_e0_not_a_directory(tmp_path):
    r = check_workspace(tmp_path / "missing")
    assert [f.code for f in r.findings] == ["E0"]


def test_e0_bad_front_matter_and_undecodable(make_ws, tmp_path):
    root = make_ws({"evidence.yml": ENTRY, "references.bib": BIB,
                    "index.qmd": '---\na: [x\n---\n[a]{.ev key="k"}\n'})
    (root / "bad.qmd").write_bytes(b"\xff\xfe\x00bad")
    r = check_workspace(root)
    assert sorted(f.file for f in r.findings if f.code == "E0") == ["bad.qmd", "index.qmd"]


def test_no_quarto_falls_back_to_root_files(make_ws):
    root = make_ws({"evidence.yml": ENTRY, "references.bib": BIB, "index.qmd": '[a]{.ev key="k"}\n'})
    r = check_workspace(root)
    assert [f.code for f in r.findings] == ["E6"]


def test_later_metadata_file_wins_and_front_matter_entries(make_ws):
    root = make_ws({
        "_quarto.yml": "metadata-files: [a.yml, b.yml]\nbibliography: references.bib\n",
        "references.bib": BIB,
        "a.yml": 'evidence:\n  k:\n    quote: "old"\n    cite: bad2020\n',
        "b.yml": 'evidence:\n  k:\n    quote: "new"\n    cite: good2020\n',
        "index.qmd": ('---\nevidence:\n  local:\n    quote: "local q"\n    cite: nope\n---\n'
                      '[a]{.ev key="k"}\n[b]{.ev key="local"}\n'),
        "other.qmd": '[c]{.ev key="local"}\n',
    })
    r = check_workspace(root)
    got = sorted((f.code, f.file, f.line, f.key) for f in r.findings if f.severity != "info")
    assert got == [("E1", "other.qmd", 1, "local"), ("E2", "other.qmd", 1, "local"),
                   ("E3", "index.qmd", 5, "local")]
