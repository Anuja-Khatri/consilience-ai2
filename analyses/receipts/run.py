"""Run every receipts analysis and write results/receipts.json and examples.json.

    python analyses/receipts/run.py            # from the repository root

Reads only the local cache (``consilience-ai2 fetch theorizer-paper-data --extract`` and
``consilience-ai2 fetch sciarena-eval``). Deterministic: fixed seeds, sorted output, so
a rerun on the same data writes the same bytes.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import precision_sample  # noqa: E402
import sciarena_analysis  # noqa: E402
import theorizer_analysis  # noqa: E402

from consilience_ai2.core.results import metric, write_results  # noqa: E402
from consilience_ai2.fetch import require  # noqa: E402
from consilience_ai2.receipts import check_workspace  # noqa: E402


def _model_id_patterns():
    spec = importlib.util.spec_from_file_location("check_secrets", REPO / "scripts" / "check_secrets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [rx for _, rx in mod.MODEL_IDS]


def model_id_screen():
    """The repository's model-identifier patterns, so no example quotes a model name."""
    pats = _model_id_patterns()
    return lambda s: any(rx.search(s) for rx in pats)


def model_id_redactor():
    """Replace each model identifier with "[model]" (for the precision sample's spans)."""
    pats = _model_id_patterns()

    def redact(s: str) -> str:
        for rx in pats:
            s = rx.sub("[model]", s)
        return s
    return redact


def seeded_metrics() -> list[dict]:
    ws = REPO / "examples" / "receipts" / "seeded"
    exp = json.loads((ws / "expected_findings.json").read_text())
    rep = check_workspace(ws, ws / exp["sources"])
    got = {(f.code, f.severity, f.file, f.line, f.key,
            (f.details or {}).get("outcome") if f.code == "E6" else None)
           for f in rep.findings if f.severity != "info"}
    planted = {tuple(x) for x in exp["planted"]}
    found = len(planted & got)
    control_files = set(exp["controls"]["files"])
    prefix = exp["controls"]["entry_prefix"]
    false = [f for f in rep.findings if f.severity != "info"
             and (f.file in control_files or (f.key or "").startswith(prefix))]
    n_control_spans = sum(1 for f in rep.findings if f.code == "E6" and f.file in control_files)
    src = "examples/receipts/seeded"
    return [
        metric("receipts.seeded.recall", round(found / len(planted), 6), n=len(planted),
               source=src, dev_or_heldout="synthetic",
               caveats=["planted defects, true by construction"],
               description="planted defects found (exact code, file, line and key)"),
        metric("receipts.seeded.unexpected_findings", len(got - planted), n=len(got),
               source=src, dev_or_heldout="synthetic", caveats=["planted defects"],
               unit="count", description="error or warning findings not in the expected file"),
        metric("receipts.seeded.control_false_findings", len(false), n=n_control_spans,
               source=src, dev_or_heldout="synthetic", caveats=["clean controls"],
               unit="count", description="error or warning findings on the clean controls"),
    ]


def asta_example_metrics() -> list[dict]:
    ws = require("asta-plugins") / "examples" / "workspace"
    rep = check_workspace(ws)
    s = rep.summary()["by_severity"]
    src = "fetch:asta-plugins"
    return [
        metric("receipts.asta_example.spans", rep.extra["checked_spans"], n=None, source=src,
               dev_or_heldout="descriptive", caveats=["examples/workspace at the pinned commit"],
               unit="count"),
        metric("receipts.asta_example.errors", s["error"], n=rep.extra["checked_spans"],
               source=src, dev_or_heldout="descriptive",
               caveats=["E6 is UNCHECKABLE: no local source text ships with the example"],
               unit="count"),
        metric("receipts.asta_example.warnings", s["warning"], n=rep.extra["checked_spans"],
               source=src, dev_or_heldout="descriptive", caveats=[], unit="count"),
    ]


def prereg_commit_hash() -> str:
    """The commit that added the preregistration (it must precede the scoring)."""
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", sciarena_analysis.PREREG],
        cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    if not out:
        raise SystemExit(f"{sciarena_analysis.PREREG} is not committed: commit it before scoring")
    return out[-1]


def main() -> int:
    is_model_id = model_id_screen()
    metrics = seeded_metrics() + asta_example_metrics()
    th_metrics, th_out = theorizer_analysis.run(is_model_id)
    metrics += th_metrics
    data = sciarena_analysis.load()
    # rules v0.1: the frozen measure of the preregistered test; never re-scored
    checked = sciarena_analysis.check_all(data, "v0.1")
    sa_metrics, sa_out = sciarena_analysis.run_descriptive(data, checked, is_model_id)
    metrics += sa_metrics
    prereg_commit = prereg_commit_hash()
    ho_metrics, ho_out = sciarena_analysis.run_heldout(data, checked, prereg_commit)
    metrics += ho_metrics
    # rules v0.2: descriptive rates only
    checked2 = sciarena_analysis.check_all(data, "v0.2")
    metrics += sciarena_analysis.run_descriptive_v02(checked2)
    pr_metrics, pr_summary = precision_sample.run(
        th_out["pool"] + sciarena_analysis.pool(data, checked, checked2), model_id_redactor())
    metrics += pr_metrics
    path = write_results("receipts", metrics, REPO / "results")
    examples = {
        "note": "Short excerpts with receipts, for illustration. The data are not copied "
                "here: each receipt names the source file, its SHA-256 and the character "
                "offsets checked. Theorizer: the released HTML export (theorizer-paper-data). "
                "SciArena: SciArena-Eval train.json.",
        "theorizer": th_out["examples"],
        "theorizer_summary": th_out["summary"],
        "sciarena": sa_out["examples"],
        "sciarena_heldout": ho_out,
        "precision_sample": pr_summary,
    }
    (HERE / "examples.json").write_text(
        json.dumps(examples, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(metrics)} metrics) and {HERE / 'examples.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
