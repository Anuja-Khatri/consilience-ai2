"""T1 attribution: what produces the dangling evidence links in the released export.

Verified facts only:

- the released export contains links to evidence records that do not exist (the
  theory-172 example below);
- asta-theorizer's HTML exporter falls back silently: ``src/ExportTheoryStoreAsHTML.py``
  line 286 at the pinned commit maps an ID with ``uuid_to_extraction_id.get(uuid, uuid)``,
  so an unmapped ID becomes its own file name.

Why those IDs are unmapped upstream is not established, and no test asserts a cause.
The upstream and data tests are skipped when the pinned sources are not in the local
cache; the synthetic test always runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from consilience_ai2.fetch import FetchError, require
from consilience_ai2.receipts import theorizer as th

COND = "html_output-literature-supported-accuracy-focused"
EXPORTER_LINE_286 = ("extraction_id = uuid_to_extraction_id.get(uuid, uuid) "
                     "if uuid_to_extraction_id else uuid")


def _require(name: str) -> Path:
    try:
        return require(name)
    except FetchError:
        pytest.skip(f"{name} is not in the local cache")


def test_exporter_falls_back_silently_at_line_286():
    root = _require("asta-theorizer")
    lines = (root / "src" / "ExportTheoryStoreAsHTML.py").read_text(encoding="utf-8").splitlines()
    assert lines[285].strip() == EXPORTER_LINE_286
    # the link it writes uses the fallback as the file name
    assert lines[286].strip().startswith('html += f\'<a href="{results_path}{extraction_id}.html')
    # Theorizer.py does not build the HTML links (the earlier attribution was wrong)
    assert "uuid_to_extraction_id" not in (root / "src" / "Theorizer.py").read_text(
        encoding="utf-8")
    assert not (root / "src" / "Pipeline.py").exists()


def test_theory_172_links_to_records_that_do_not_exist():
    zpath = _require("theorizer-paper-data")
    cdir = zpath.with_suffix("") / COND
    if not cdir.is_dir():
        pytest.skip("theorizer-paper-data is not extracted")
    records, _ = th.load_records(cdir)
    theory = th.parse_theory((cdir / "theories" / "theory-172.html").read_text(encoding="utf-8"),
                             "theories/theory-172.html")
    findings, _ = th.check_theory(theory, records, COND)
    t1 = {(f.details["id"], f.details["href"]) for f in findings
          if f.code == "T1" and f.details["id"].startswith("e2232.")}
    want = {(f"e2232.{k}", f"../results/e2232.{k}.html#e2232.{k}") for k in range(5, 10)}
    assert t1 == want
    for k in range(5, 10):
        assert not (cdir / "results" / f"e2232.{k}.html").exists()
    held = th.parse_results_file(
        (cdir / "results" / "extraction-result-2232.html").read_text(encoding="utf-8"),
        "results/extraction-result-2232.html")
    assert [r.id for r in held] == [f"e2232.{k}" for k in range(5)]


def test_fallback_link_is_counted_as_t1_synthetic():
    """The exporter's two link forms, written by hand: a mapped ID and a fallback."""
    theory_html = (
        "<p><strong>Name:</strong> t</p>"
        "<h3>Statement 0: law</h3><p><strong>Statement:</strong> X rises.</p>"
        "<p><strong>Domain/Scope:</strong> all</p>"
        "<h4>Supporting Evidence for this Law</h4><ol>\n"
        '    <li>Item. <a href="../results/extraction-result-7.html#e7.0" '
        'class="evidence-link">[e7.0]</a> '
        '<a href="../results/e7.1.html#e7.1" class="evidence-link">[e7.1]</a> </li>\n</ol>')
    results_html = ('<div class="extraction-instance-container" id="e7.0">'
                    "<table><tr><td><strong>f</strong></td><td>X rises.</td></tr></table></div>")
    records = {r.id: r for r in th.parse_results_file(results_html,
                                                       "results/extraction-result-7.html")}
    findings, _ = th.check_theory(th.parse_theory(theory_html, "theories/theory-1.html"),
                                  records, "c")
    t1 = [f for f in findings if f.code == "T1"]
    assert [(f.details["id"], f.details["href"]) for f in t1] == [
        ("e7.1", "../results/e7.1.html#e7.1")]
