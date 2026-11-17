"""The CodeScientist adapter on a synthetic experiment directory (and the same in a zip)."""

from __future__ import annotations

import json
import zipfile

from consilience_ai2.audit import Tree, audit_path, detect_format, load_codescientist
from consilience_ai2.audit.adapters import latex_mask

REPORT = r"""\documentclass[11pt]{article}
\usepackage{booktabs}
\begin{document}
\begin{abstract}
The agent outperforms a random baseline (0.343 vs 0.175, p < 0.001) across 25 episodes.
\end{abstract}
\begin{figure}[h]
\includegraphics[width=0.8\linewidth]{to_save/plot.pdf}
\end{figure}
Mean scores were 0.343 and 0.175.
\end{document}
"""
MAIN = """import json
NUM_EPISODES = 25
scores = {"random": [0.1] * NUM_EPISODES, "container": [0.3] * NUM_EPISODES}
print(json.dumps(scores))
"""


def make_experiment(root, name="containeragentcopy1-20250101-000000"):
    d = root / name
    run = d / "modal-python-20250101-000100" / "modal-output"
    run.mkdir(parents=True)
    (d / "modal-python-20250101-000000").mkdir()
    (run.parent / "main.py").write_text(MAIN)
    (run / "results.json").write_text(json.dumps({
        "pilot_mode": "PILOT", "config": {"num_episodes": 25},
        "statistics": {"mean_baseline": 0.1754, "mean_experimental": 0.34323,
                       "p_value": 0.0, "dataset_size": 25}}))
    (run / "log.json").write_text(json.dumps([{"type": "info", "message": "done"}]))
    (run / "stdout.python.txt").write_text("")
    (d / "report").mkdir()
    (d / "report" / "report.tex").write_text(REPORT)
    (d / "history.json").write_text(json.dumps({"metadata": {"interesting_results": True,
                                                             "current_pilot_mode": "PILOT"},
                                                "history": []}))
    return d


def test_codescientist_experiment(tmp_path):
    d = make_experiment(tmp_path)
    assert detect_format(d) == "codescientist"
    data, _ = audit_path(d)
    node = data["nodes"][0]
    codes = {c["code"] for c in node["checks"] if c["severity"] in ("error", "warning")}
    assert "R1" in codes and "A1" not in codes  # 0.8 in the figure options is masked
    assert node["meta"]["final_run"] == "modal-python-20250101-000100"
    assert node["meta"]["claim_source"] == "report/report.tex"
    a2 = [c for c in node["checks"] if c["code"] == "A2"]
    assert a2 and all(c["severity"] == "info" for c in a2)


def test_directory_of_experiments_and_zip_reading(tmp_path):
    make_experiment(tmp_path / "batch", "aaacopy1-20250101-000000")
    make_experiment(tmp_path / "batch", "aaacopy2-20250101-000001")
    run = load_codescientist(tmp_path / "batch")
    assert [n.id for n in run.nodes] == ["aaacopy1-20250101-000000", "aaacopy2-20250101-000001"]
    zpath = tmp_path / "b.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for p in sorted((tmp_path / "batch").rglob("*")):
            if p.is_file():
                z.write(p, "top/" + p.relative_to(tmp_path / "batch").as_posix())
    zrun = load_codescientist(Tree(zf=zipfile.ZipFile(zpath), prefix="top"))
    assert [n.id for n in zrun.nodes] == [n.id for n in run.nodes]
    from consilience_ai2.audit.engine import audit

    a, _ = audit(run)
    b, _ = audit(zrun)
    assert [n["codes"] for n in a["nodes"]] == [n["codes"] for n in b["nodes"]]


def test_latex_mask_covers_preamble_and_options():
    spans = latex_mask(REPORT)
    i = REPORT.index("0.8")
    assert any(s <= i < e for s, e in spans)
    j = REPORT.index("0.343")
    assert not any(s <= j < e for s, e in spans)
