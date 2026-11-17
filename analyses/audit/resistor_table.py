"""Reproduce a published number: the CodeScientist resistor report's success-rate table.

Discovery 4 of CodeScientist Table 4 (``resistorsubstitutionadvisor``) reports a table of
success rates "within 1%, 5% and 10%" per method. Each cell is recomputed from the final
run's ``results.json`` (one record per method, target and trial, with boolean
``within_1_percent``/``within_5_percent``/``within_10_percent``) as 100 x the mean of the
boolean over that method's records, and compared with the printed cell at its printed
precision. tests/audit/test_resistor_table.py asserts that every cell agrees.
"""

from __future__ import annotations

import json

from codescientist_common import EXAMPLES_PREFIX, example_dirs, examples_zip

from consilience_ai2.audit import Tree
from consilience_ai2.audit.adapters import _cs_final_dir
from consilience_ai2.audit.tables import cell_agrees, latex_tables
from consilience_ai2.core.hashing import sha256_bytes
from consilience_ai2.core.results import metric

KEYS = ("within_1_percent", "within_5_percent", "within_10_percent")


def reproduce(tree: Tree) -> dict:
    final = _cs_final_dir(tree)
    res_rel = f"{final}/modal-output/results.json"
    rep_rel = "report/report.tex"
    res_b, rep_b = tree.read(res_rel), tree.read(rep_rel)
    records = json.loads(res_b)
    report = rep_b.decode("utf-8")
    rates: dict[str, list[float]] = {}
    for method in sorted({r["method"] for r in records}):
        sub = [r for r in records if r["method"] == method]
        rates[method] = [100.0 * sum(bool(r[k]) for r in sub) / len(sub) for k in KEYS]
    table = next(t for t in latex_tables(report) if "Within" in " ".join(t.header))
    cells = []
    for row in table.body():
        method = row[0]
        for i, cell in enumerate(row[1:4]):
            ok = cell_agrees(cell, rates[method][i])
            cells.append({"method": method, "column": KEYS[i], "printed": cell,
                          "recomputed": round(rates[method][i], 6), "agrees": ok})
    return {"cells": cells, "results_file": res_rel, "results_sha256": sha256_bytes(res_b),
            "report_file": rep_rel, "report_sha256": sha256_bytes(rep_b),
            "n_records": len(records)}


def run() -> tuple[list[dict], dict]:
    d = next(x for x in example_dirs() if x.startswith("resistorsubstitutionadvisor"))
    out = reproduce(Tree(zf=examples_zip(), prefix=EXAMPLES_PREFIX + d))
    agree = sum(1 for c in out["cells"] if c["agrees"])
    ms = [metric("audit.resistor_table.cells_reproduced", agree, n=len(out["cells"]),
                 source="fetch:codescientist-example-experiments", dev_or_heldout="descriptive",
                 caveats=["one table in one report; the recomputation (100 x mean of the "
                          "within_k_percent booleans per method) was chosen to match the "
                          "table's column names"],
                 unit="table cells",
                 receipts=[f"{d}/{out['results_file']} sha256:{out['results_sha256']}",
                           f"{d}/{out['report_file']} sha256:{out['report_sha256']}"])]
    return ms, out
