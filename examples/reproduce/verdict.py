"""Read every reproduction record and write the verdicts from the numbers. Exits non-zero on any error.

    uv run --no-project --with "consilience-ai2[consilience]" python -I scripts/verdict.py [records...]

A drop-in for the asta-flows "Secondary reproduction" workflow, in the pattern of the
exploration's check.py and runlog.py: put it in the run's scripts/ directory. It reads
reproduction/*.yaml (one record per hypothesis; see the record schema in consilience-ai2)
and writes:
  reproduction/reproduction_verdict.json   every record's checks (F1 D1 V1 P1 P2) with receipts
  reproduction/mission_verdicts.txt        the REPRODUCED / NOT REPRODUCED / UNDECIDED block of
                                           the workflow's mission.md, filled from the numbers
The verdict comes from the committed thresholds and the recorded effect, p and n, never from
the prose. Commit each record's thresholds before its result: P1 reads the git history.
"""

import json
import sys
from pathlib import Path

import yaml

from consilience_ai2.reproduce import check_file

ROOT = Path(__file__).resolve().parent.parent
REPRO = ROOT / "reproduction"
OUT = REPRO / "reproduction_verdict.json"
MISSION = REPRO / "mission_verdicts.txt"


def effect_text(m: dict) -> str:
    """'r = 0.27, p = 0.0002, n = 180' from a record's measurement, as written."""
    parts = []
    es = m.get("effect_size") or {}
    if es.get("value") is not None:
        parts.append(f"{es['type']} = {es['value']}")
    elif m.get("value") is not None:
        parts.append(f"{m['value']} {m.get('unit', '')}".strip())
    for k in ("p", "n"):
        if m.get(k) is not None:
            parts.append(f"{k} = {m[k]}")
    return ", ".join(parts) or "no numbers"


def main(paths: list[str]) -> int:
    records = [Path(p) for p in paths] or sorted(REPRO.glob("*.yaml"))
    if not records:
        print(f"no records in {REPRO}", file=sys.stderr)
        return 2
    reports, bins = [], {"reproduced": [], "not_reproduced": [], "inconclusive": []}
    failed = False
    for path in records:
        report = check_file(path, repo=ROOT)
        reports.append(report.to_dict())
        print("\n".join(report.annotations()))
        failed |= report.exit_code() == 1
        v = report.extra.get("verdict")
        if not v:
            continue
        rec = yaml.safe_load(path.read_text(encoding="utf-8"))
        line = (f"- {rec['source_hypothesis']}\n"
                f"    source: {effect_text(rec['source'])}   "
                f"independent: {effect_text(rec['reproduction'])}")
        if v["verdict"] == "not_reproduced":
            line += f"   ({v['outcome'].replace('_', ' ')})"
        if v["verdict"] == "inconclusive":
            line += f"   ({v['reason'] or v['outcome']})"
        for c in v.get("caveats", []):
            line += f"\n    caveat: {c}"
        bins[v["verdict"]].append(line)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"version": 1, "records": reports}, sort_keys=True, indent=2,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    text = ["REPRODUCED:", *bins["reproduced"],
            "NOT REPRODUCED (opposite effect, or rejected):", *bins["not_reproduced"],
            "UNDECIDED, with the reason:", *bins["inconclusive"]]
    MISSION.write_text("\n".join(text) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} and {MISSION.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
