"""LaTeX tables, and the CodeScientist resistor table reproduced from its results.json."""

from __future__ import annotations

import json
import zipfile

import pytest

from consilience_ai2.audit import Tree
from consilience_ai2.audit.adapters import _cs_final_dir
from consilience_ai2.audit.tables import cell_agrees, latex_tables

TEX = r"""\begin{tabular}{lcc}
\toprule
Method & Within 1\% & Within 5\% \\
\midrule
A & 24.0\% & 39.3\% \\
B & 94.0\% & 98.0\% \\
\bottomrule
\end{tabular}"""


def test_latex_tables_and_cells():
    t = latex_tables(TEX)[0]
    assert t.header == ["Method", r"Within 1\%", r"Within 5\%"]
    assert t.body()[0] == ["A", r"24.0\%", r"39.3\%"]
    assert cell_agrees(r"39.3\%", 39.3333) is True
    assert cell_agrees(r"39.3\%", 39.36) is False
    assert cell_agrees("A", 1.0) is None


KEYS = ("within_1_percent", "within_5_percent", "within_10_percent")


def test_resistor_report_table_reproduces_exactly():
    """CodeScientist Table 4 #4: every success-rate cell in report.tex equals 100 x the
    mean of the matching boolean in the final run's results.json, per method."""
    from consilience_ai2.fetch import FetchError, require

    try:
        zpath = require("codescientist-example-experiments")
    except FetchError:
        pytest.skip("codescientist-example-experiments not fetched")
    z = zipfile.ZipFile(zpath)
    prefix = "example-experiments/"
    d = sorted({n[len(prefix):].split("/", 1)[0] for n in z.namelist()
                if n.startswith(prefix + "resistorsubstitutionadvisor")})[0]
    t = Tree(zf=z, prefix=prefix + d)
    records = json.loads(t.read(f"{_cs_final_dir(t)}/modal-output/results.json"))
    table = next(tb for tb in latex_tables(t.read("report/report.tex").decode())
                 if "Within" in " ".join(tb.header))
    assert [r[0] for r in table.body()] == ["LLM", "Simple", "Mathematical"]
    checked = 0
    for row in table.body():
        sub = [r for r in records if r["method"] == row[0]]
        for i, k in enumerate(KEYS):
            rate = 100.0 * sum(bool(r[k]) for r in sub) / len(sub)
            assert cell_agrees(row[1 + i], rate) is True, (row[0], k, row[1 + i], rate)
            checked += 1
    assert checked == 9
