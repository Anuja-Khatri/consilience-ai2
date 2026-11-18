"""The seeded-defect workspace: every planted defect found, nothing on the controls."""

from __future__ import annotations

import json
from collections import Counter

from consilience_ai2.cli import main
from consilience_ai2.receipts import check_workspace


def _items(report):
    return Counter(
        (f.code, f.severity, f.file, f.line, f.key,
         (f.details or {}).get("outcome") if f.code == "E6" else None)
        for f in report.findings)


def _expected(seeded):
    exp = json.loads((seeded / "expected_findings.json").read_text())
    planted = Counter(tuple(x) for x in exp["planted"])
    receipts = Counter(tuple(x) for x in exp["receipts"])
    return exp, planted, receipts


def test_every_planted_defect_found_exactly(seeded):
    exp, planted, receipts = _expected(seeded)
    assert exp["flags"] == ["--with-w2"]
    report = check_workspace(seeded, seeded / exp["sources"], with_w2=True)
    got = _items(report)
    got_defects = Counter({k: v for k, v in got.items() if k[1] != "info"})
    got_receipts = Counter({k: v for k, v in got.items() if k[1] == "info"})
    assert got_defects == planted
    assert got_receipts == receipts


def test_w2_is_opt_in(seeded):
    """Without with_w2 the planted W2 is not reported; every other finding is the same."""
    exp, planted, receipts = _expected(seeded)
    report = check_workspace(seeded, seeded / exp["sources"])
    got = _items(report)
    no_w2 = Counter({k: v for k, v in planted.items() if k[0] != "W2"})
    assert Counter({k: v for k, v in got.items() if k[1] != "info"}) == no_w2
    assert Counter({k: v for k, v in got.items() if k[1] == "info"}) == receipts
    assert "W2" not in report.extra["checks"]
    on = check_workspace(seeded, seeded / exp["sources"], with_w2=True)
    assert on.extra["checks"] == ["E0", "E1", "E2", "E3", "E4", "E5", "E6", "W1", "W2"]


def test_every_code_is_planted(seeded):
    _, planted, _ = _expected(seeded)
    codes = {k[0] for k in planted}
    assert codes == {"E1", "E2", "E3", "E4", "E5", "E6", "W1", "W2"}


def test_no_finding_on_controls(seeded):
    exp, _, _ = _expected(seeded)
    report = check_workspace(seeded, seeded / exp["sources"], with_w2=True)
    for f in report.findings:
        if f.severity == "info":
            continue
        assert f.file not in exp["controls"]["files"], f
        assert not (f.key or "").startswith(exp["controls"]["entry_prefix"]), f
    found = [f for f in report.findings if f.file == "controls.qmd"]
    assert found and all(f.code == "E6" and f.details["outcome"] == "FOUND" for f in found)


def test_found_receipts_point_at_the_quote(seeded):
    from consilience_ai2.core.normalise import NORMALISATION_VERSION, normalise

    report = check_workspace(seeded, seeded / "sources")
    store_quotes = {
        "c-ligature": "The final score was 0.42 ± 0.03 across five seeds.",
        "c-hyphenation": "Prior work reported a 12% gain in a related setting",
        "c-curly-quotes": 'measured with "paired" comparisons',
    }
    by_key = {f.key: f for f in report.findings if f.code == "E6" and f.file == "controls.qmd"}
    for key, quote in store_quotes.items():
        f = by_key[key]
        r = f.receipt
        assert r.normalisation == NORMALISATION_VERSION
        src = (seeded / "sources" / r.source.removeprefix("file:")).read_text(encoding="utf-8")
        assert normalise(src[r.offset:r.end]) == normalise(quote)
        import hashlib
        assert r.sha256 == hashlib.sha256(
            (seeded / "sources" / r.source.removeprefix("file:")).read_bytes()).hexdigest()


def test_reruns_are_byte_identical(seeded, tmp_path):
    a = check_workspace(seeded, seeded / "sources").to_json()
    b = check_workspace(seeded, seeded / "sources").to_json()
    assert a == b
    assert "created" not in json.loads(a)


def test_report_shape(seeded):
    d = check_workspace(seeded, seeded / "sources").to_dict()
    assert d["version"] == 1
    assert d["tool"] == "consilience-ai2 receipts"
    assert d["checked_spans"] == 26
    assert d["entries"] == 20
    assert d["rules"]["certainty_words"].startswith("consilience-ai2.certainty/")
    paths = {i["path"] for i in d["inputs"]}
    assert {"evidence.yml", "references.bib", "_quarto.yml", "controls.qmd",
            "defects.qmd", "sources/smith2024.txt"} <= paths
    assert all(len(i["sha256"]) == 64 for i in d["inputs"])


def test_cli_exit_codes_annotations_and_json(seeded, clean, tmp_path, capsys):
    out = tmp_path / "r.json"
    rc = main(["receipts", "check", str(seeded), "--sources", str(seeded / "sources"),
               "--json", str(out)])
    assert rc == 1
    lines = capsys.readouterr().out.splitlines()
    assert "::error file=defects.qmd,line=7::E1 .ev span references unknown key \"d-missing-key\"" in lines
    assert not any("::W2 " in ln for ln in lines)  # W2 is opt-in
    assert any(ln.startswith("::warning file=defects.qmd,line=25::W1 ") for ln in lines)
    rc = main(["receipts", "check", str(seeded), "--sources", str(seeded / "sources"),
               "--with-w2"])
    assert rc == 1
    lines = capsys.readouterr().out.splitlines()
    assert any(ln.startswith("::warning file=defects.qmd,line=29::W2 ") for ln in lines)
    assert not any(ln.startswith("::notice") for ln in lines)
    assert json.loads(out.read_text())["summary"]["by_severity"]["error"] == 14
    assert main(["receipts", "check", str(clean), "--sources", str(clean / "sources")]) == 0
    assert main(["receipts", "check", str(clean)]) == 0  # E6 UNCHECKABLE does not fail


def test_cli_fail_on_warnings_and_usage(seeded, make_ws, tmp_path):
    ws = make_ws({
        "_quarto.yml": "metadata-files: [evidence.yml]\n",
        "evidence.yml": 'evidence:\n  k:\n    quote: "it may help"\n',
        "index.qmd": '[It proves 3 things]{.ev key="k"}\n',
    })
    assert main(["receipts", "check", str(ws)]) == 0
    assert main(["receipts", "check", str(ws), "--fail-on-warnings"]) == 1  # W1 on "3"
    w2_only = make_ws({
        "evidence.yml": 'evidence:\n  k:\n    quote: "it may help"\n',
        "index.qmd": '[It proves this]{.ev key="k"}\n',
    })
    assert main(["receipts", "check", str(w2_only), "--fail-on-warnings"]) == 0
    assert main(["receipts", "check", str(w2_only), "--with-w2", "--fail-on-warnings"]) == 1
    assert main(["receipts", "check", str(ws), "--sources", str(tmp_path / "nope")]) == 2
    assert main(["receipts"]) == 2


def test_all_annotations_prints_receipts(clean, capsys):
    main(["receipts", "check", str(clean), "--sources", str(clean / "sources"),
          "--all-annotations"])
    out = capsys.readouterr().out
    assert "::notice file=index.qmd,line=5::E6 FOUND in file:lee2023.txt" in out
