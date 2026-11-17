"""The CLI, exit codes and byte-identical reruns."""

from __future__ import annotations

import json
import shutil

from consilience_ai2.cli import main


def test_cli_run_writes_report_and_exit_code(ad_examples, tmp_path, capsys):
    out = tmp_path / "va.json"
    code = main(["audit", "run", str(ad_examples / "synthetic_run"), "--json", str(out)])
    assert code == 1  # the fixtures plant error-severity defects
    data = json.loads(out.read_text())
    assert data["version"] == 1 and data["tool"] == "consilience-ai2 audit"
    assert {"run", "n_nodes", "n_with_pvalue", "nodes", "findings", "summary"} <= set(data)
    for n in data["nodes"]:
        assert set(n) >= {"id", "llm_validity_check", "checks", "q_value", "verdict"}
        assert n["verdict"] in ("pass", "flag", "refuse")
    printed = capsys.readouterr().out
    assert "node_2_1: refuse" in printed and "::error" in printed


def test_cli_default_output_path_and_byte_identical(ad_examples, tmp_path):
    run = tmp_path / "run"
    shutil.copytree(ad_examples / "synthetic_run", run)
    assert main(["audit", "run", str(run), "--format", "autodiscovery",
                 "--metadata", str(run / "dataset_metadata.json")]) == 1
    first = (run / "validity_audit.json").read_bytes()
    main(["audit", "run", str(run)])
    assert (run / "validity_audit.json").read_bytes() == first


def test_cli_clean_run_exits_zero(ad_examples, tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    shutil.copy(ad_examples / "synthetic_run" / "mcts_node_2_0.json", run)
    assert main(["audit", "run", str(run), "--json", str(tmp_path / "o.json")]) == 0


def test_cli_errors(tmp_path):
    assert main(["audit", "run", str(tmp_path / "missing")]) == 1
    (tmp_path / "empty").mkdir()
    assert main(["audit", "run", str(tmp_path / "empty")]) == 1
    assert main(["audit"]) == 2
