import json

import pytest

from consilience_ai2.core.findings import (
    Finding,
    InputRecord,
    Receipt,
    Report,
)
from consilience_ai2.core.hashing import sha256_text
from consilience_ai2.core.normalise import NORMALISATION_VERSION

H = sha256_text("source text")


def make_report(order=1):
    findings = [
        Finding("E6", "error", "quote not verbatim", file="index.qmd", line=42, key="k1",
                receipt=Receipt("paperstore:123", H, offset=None)),
        Finding("E6", "info", "FOUND", file="index.qmd", line=7, key="k2",
                receipt=Receipt("paperstore:123", H, offset=10, end=25,
                                normalisation=NORMALISATION_VERSION)),
        Finding("W1", "warning", "0.42 absent from quote", file="a.qmd", line=3, key="k3",
                details={"span": "r = 0.42", "numbers": ["0.42"]}),
    ]
    r = Report(tool="consilience-ai2 receipts", tool_version="0.1.0",
               inputs=[InputRecord("evidence.yml", H, "evidence"), InputRecord("a.qmd", H)],
               extra={"checked_spans": 3})
    r.extend(findings if order == 1 else list(reversed(findings)))
    return r


def test_json_is_deterministic_and_order_independent():
    a, b = make_report(1).to_json(), make_report(2).to_json()
    assert a == b
    d = json.loads(a)
    assert d["version"] == 1 and d["checked_spans"] == 3
    assert [f["line"] for f in d["findings"]] == [3, 7, 42]  # sorted by file, line
    assert "created" not in d  # no timestamp unless passed in
    assert list(d) == sorted(d)


def test_summary_counts():
    s = make_report().summary()
    assert s == {"total": 3, "by_severity": {"error": 1, "warning": 1, "info": 1},
                 "by_code": {"E6": 2, "W1": 1}}


def test_exit_code():
    r = make_report()
    assert r.exit_code() == 1
    assert r.exit_code(fail_on=("critical",)) == 0
    assert Report("t", "0").exit_code() == 0


def test_roundtrip():
    r = make_report()
    r.created = "2026-01-01T00:00:00Z"
    back = Report.from_dict(json.loads(r.to_json()))
    assert back.to_json() == r.to_json()


def test_receipt_fields():
    rec = Receipt("file:x.txt", H, offset=3, end=9, normalisation=NORMALISATION_VERSION)
    assert rec.to_dict() == {"source": "file:x.txt", "sha256": H, "offset": 3, "end": 9,
                             "normalisation": NORMALISATION_VERSION}
    assert Receipt.from_dict(rec.to_dict()) == rec


@pytest.mark.parametrize("kw", [
    {"source": "", "sha256": H},
    {"source": "s", "sha256": "ABC"},
    {"source": "s", "sha256": H, "offset": -1},
    {"source": "s", "sha256": H, "end": 3},
    {"source": "s", "sha256": H, "offset": 5, "end": 3},
])
def test_receipt_validation(kw):
    with pytest.raises(ValueError):
        Receipt(**kw)


@pytest.mark.parametrize("kw", [
    {"code": "e1", "severity": "error", "message": "m"},
    {"code": "E1", "severity": "fatal", "message": "m"},
    {"code": "E1", "severity": "error", "message": "m", "line": 0},
    {"code": "E1", "severity": "error", "message": "m", "details": {"x": float("nan")}},
    {"code": "E1", "severity": "error", "message": "m", "details": {"x": object()}},
])
def test_finding_validation(kw):
    with pytest.raises(ValueError):
        Finding(**kw)


def test_extra_cannot_override_schema():
    r = Report("t", "0", extra={"findings": []})
    with pytest.raises(ValueError):
        r.to_dict()


def test_annotations():
    assert Finding("E1", "error", 'unknown key "x"', file="index.qmd", line=42).to_annotation() \
        == '::error file=index.qmd,line=42::E1 unknown key "x"'
    assert Finding("W2", "warning", "may -> shows", file="a.qmd").to_annotation() \
        == "::warning file=a.qmd::W2 may -> shows"
    assert Finding("A5", "info", "q=0.12").to_annotation() == "::notice::A5 q=0.12"
    # escaping: newlines and % in data; ':' and ',' in properties
    ann = Finding("E2", "error", "50% of\nquotes", file="dir:a,b.qmd", line=1).to_annotation()
    assert ann == "::error file=dir%3Aa%2Cb.qmd,line=1::E2 50%25 of%0Aquotes"


def test_report_annotations_sorted():
    lines = make_report(2).annotations()
    assert lines[0].startswith("::warning file=a.qmd,line=3::W1")
    assert len(lines) == 3


def test_input_from_file(tmp_path):
    p = tmp_path / "sub" / "evidence.yml"
    p.parent.mkdir()
    p.write_text("evidence: {}\n")
    rec = InputRecord.from_file(p, role="evidence", relative_to=tmp_path)
    assert rec.path == "sub/evidence.yml" and rec.sha256 == sha256_text("evidence: {}\n")


def test_write(tmp_path):
    out = make_report().write(tmp_path / "out" / "report.json")
    assert out.read_text() == make_report().to_json()
