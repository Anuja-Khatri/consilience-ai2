"""P2 verbatim hypothesis, the CLI, the report format and byte-identical reruns."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest

from consilience_ai2.cli import main
from consilience_ai2.reproduce import check_hypothesis, evaluate, parse


def test_p2_verbatim_after_normalisation(record):
    rec = record(hypothesis="Longer   sleep is associated with “better” recall.",
                 source_hypothesis='Longer sleep is associated with "better" recall.')
    assert check_hypothesis(parse(rec)).cls == "verbatim"


def test_p2_reworded(record):
    out = check_hypothesis(parse(record(hypothesis="Longer sleep improves recall.")))
    assert out.cls == "reworded" and out.first_difference == len("Longer sleep i")


def test_p2_case_counts(record):
    assert check_hypothesis(parse(record(
        hypothesis="longer sleep is associated with better recall."))).cls == "reworded"


def test_p2_uncheckable(record):
    assert check_hypothesis(parse(record(hypothesis="  "))).cls == "uncheckable"


@pytest.mark.parametrize("over,severity", [({}, "info"),
                                           ({"hypothesis": "Sleep helps."}, "error"),
                                           ({"hypothesis": ""}, "warning")])
def test_p2_finding(record, over, severity):
    rep = evaluate(record(over), backend="fallback", skip=("P1",))
    f = next(x for x in rep.findings if x.code == "P2")
    assert f.severity == severity
    assert f.receipt.normalisation == "consilience-ai2.normalise/1"


def test_cli_writes_report_beside_record(tmp_path, examples_dir, capsys):
    rec = tmp_path / "supported.yaml"
    shutil.copy(examples_dir / "records" / "supported.yaml", rec)
    code = main(["reproduce", "check", str(rec), "--backend", "fallback"])
    out = json.loads((tmp_path / "reproduction_verdict.json").read_text())
    assert code == 0
    assert out["verdict"]["verdict"] == "reproduced"
    assert out["tool"] == "consilience-ai2 reproduce" and out["version"] == 1
    assert set(out["summary"]["by_code"]) == {"F1", "D1", "V1", "P1", "P2"}
    printed = capsys.readouterr().out
    assert "::notice file=supported.yaml" in printed and "wrote" in printed


def test_cli_json_to_stdout_and_skip(examples_dir, capsys):
    code = main(["reproduce", "check", str(examples_dir / "records" / "underpowered.yaml"),
                 "--json", "-", "--skip", "P1", "--backend", "fallback"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["checks_skipped"] == ["P1"]
    assert out["verdict"]["decidability"] == "underpowered"


@pytest.mark.parametrize("name,expected", [("substitution.yaml", 1), ("supported.yaml", 0),
                                           ("proxy_rejected.yaml", 0)])
def test_cli_exit_codes(examples_dir, tmp_path, name, expected):
    code = main(["reproduce", "check", str(examples_dir / "records" / name), "--json",
                 str(tmp_path / "v.json"), "--skip", "P1", "--backend", "fallback"])
    assert code == expected


def test_cli_usage_errors(tmp_path, capsys, monkeypatch):
    assert main(["reproduce", "check", str(tmp_path / "missing.yaml")]) == 2
    assert main(["reproduce"]) == 2
    import consilience_ai2.reproduce.comparability as c

    monkeypatch.setattr(c, "consilience_version", lambda: None)
    f = tmp_path / "r.yaml"
    f.write_text("schema_version: 1\n", encoding="utf-8")
    assert main(["reproduce", "check", str(f), "--backend", "consilience"]) == 2


def test_cli_invalid_record_exits_1(tmp_path):
    f = tmp_path / "r.yaml"
    f.write_text("schema_version: 1\nid: x\n", encoding="utf-8")
    assert main(["reproduce", "check", str(f), "--json", str(tmp_path / "o.json")]) == 1
    out = json.loads((tmp_path / "o.json").read_text())
    assert out["findings"][0]["code"] == "S1" and out["verdict"] is None


def test_byte_identical_reruns(examples_dir, tmp_path):
    outs = []
    for i in range(2):
        o = tmp_path / f"v{i}.json"
        main(["reproduce", "check", str(examples_dir / "records" / "proxy_rejected.yaml"),
              "--json", str(o), "--backend", "fallback"])
        outs.append(o.read_bytes())
    assert outs[0] == outs[1]
    assert b"created" not in outs[0]


@pytest.mark.parametrize("name", ["supported", "underpowered", "proxy_rejected", "substitution",
                                  "equivalence_units"])
def test_examples_give_their_documented_verdicts(examples_dir, name):
    from consilience_ai2.reproduce import check_file

    expected = {"supported": "supported", "underpowered": "undecided(underpowered)",
                "proxy_rejected": "rejected", "substitution": "not_a_reproduction",
                "equivalence_units": "supported"}[name]
    backend = "auto" if name == "equivalence_units" else "fallback"
    if name == "equivalence_units":
        pytest.importorskip("consilience")
    rep = check_file(examples_dir / "records" / f"{name}.yaml", backend=backend, skip=("P1",))
    assert rep.extra["verdict"]["outcome_label"] == expected


def test_dropin_verdict_script(examples_dir, git_repo):
    (git_repo.root / "scripts").mkdir()
    shutil.copy(examples_dir / "verdict.py", git_repo.root / "scripts" / "verdict.py")
    (git_repo.root / "reproduction").mkdir()
    for name in ("supported", "proxy_rejected", "underpowered"):
        shutil.copy(examples_dir / "records" / f"{name}.yaml",
                    git_repo.root / "reproduction" / f"{name}.yaml")
    git_repo.commit("records")
    p = subprocess.run([sys.executable, "-I", "scripts/verdict.py"], cwd=git_repo.root,
                       capture_output=True, text=True)
    # every record and its thresholds were committed together: P1 same_commit is an error
    assert p.returncode == 1, p.stderr
    mission = (git_repo.root / "reproduction" / "mission_verdicts.txt").read_text()
    assert mission.index("REPRODUCED:") < mission.index("Longer nightly sleep")
    assert "(rejected)" in mission and "(underpowered)" in mission
    assert "caveat: proxy:" in mission
    data = json.loads((git_repo.root / "reproduction" / "reproduction_verdict.json").read_text())
    assert len(data["records"]) == 3
