#!/usr/bin/env python3
"""Run every C2 analysis and write ``results/audit.json``.

    python analyses/audit/run_all.py

Reads only fetched data (``consilience_ai2.fetch.require``); no network, no model calls,
fixed seeds. Re-running on the same data gives the same bytes. Writes:

- ``results/audit.json``: every metric (``write_results("audit", ...)``);
- ``analyses/audit/dev_table.md``: the per-discovery dev table;
- ``analyses/audit/details/*.json``: per-analysis details (codes per run, exclusions).

The held-out analysis (``codescientist_heldout.py``) runs only once its
preregistration (``prereg/audit/heldout_prereg.md``) is committed. It is the rules v0.1
result and always runs with the frozen v0.1 rules (``rules_versions``); the dev analysis
reports v0.1 (frozen) and v0.2 (working copy) side by side. The v0.2 held-out test
(``codescientist_heldout_v2.py``) runs only once ``prereg/audit/heldout_v2_prereg.md`` is
committed.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

from rules_versions import V01, run_under  # noqa: E402

from consilience_ai2.core.results import write_results  # noqa: E402

MODULES = ["codescientist_dev", "resistor_table", "discoverybench_a5"]
HELDOUT = "codescientist_heldout"            # rules v0.1, preregistered, frozen rules
HELDOUT_V2 = "codescientist_heldout_v2"      # rules v0.2, preregistered separately
PREREG_V2 = REPO / "prereg" / "audit" / "heldout_v2_prereg.md"


def _dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def main() -> int:
    metrics = []
    details_dir = HERE / "details"
    details_dir.mkdir(exist_ok=True)
    mods = list(MODULES)
    if (HERE / f"{HELDOUT}.py").exists():
        mods.append(HELDOUT)
    if (HERE / f"{HELDOUT_V2}.py").exists() and PREREG_V2.exists():
        mods.append(HELDOUT_V2)
    for name in mods:
        mod = importlib.import_module(name)
        if name == HELDOUT:
            ms, info = run_under(V01, name)
        else:
            ms, info = mod.run()
        metrics.extend(ms)
        (details_dir / f"{name}.json").write_text(_dump(info), encoding="utf-8")
        if name == "codescientist_dev":
            (HERE / "dev_table.md").write_text(mod.table_md(info), encoding="utf-8")
        print(f"{name}: {len(ms)} metrics", file=sys.stderr)
    path = write_results("audit", metrics, results_dir=REPO / "results")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
