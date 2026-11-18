"""The commit-order demo (``examples/reproduce/demo_commit_order.py``): thresholds in an
earlier commit than the result pass P1 and the check exits 0; the same record committed
in one commit is ``same_commit``."""

from __future__ import annotations

import shutil
import subprocess
import sys

import yaml

from consilience_ai2.reproduce import check_file


def test_demo_passes_p1_and_exits_zero(examples_dir):
    p = subprocess.run([sys.executable, str(examples_dir / "demo_commit_order.py")],
                       capture_output=True, text=True, check=False)
    assert p.returncode == 0, p.stdout + p.stderr
    out = p.stdout
    assert "P1 commit order: committed_first" in out
    assert "V1 verdict from the numbers: reproduced (supported)" in out
    assert "::error" not in out and out.rstrip().endswith("exit 0")
    again = subprocess.run([sys.executable, str(examples_dir / "demo_commit_order.py")],
                           capture_output=True, text=True, check=False)
    assert again.stdout == out  # byte-identical rerun


def test_demo_plan_stage_has_no_result(examples_dir):
    sys.path.insert(0, str(examples_dir))
    try:
        import demo_commit_order as demo
    finally:
        sys.path.remove(str(examples_dir))
    full = yaml.safe_load((examples_dir / "records" / "committed_first.yaml").read_text())
    plan = demo.plan_stage(full)
    assert plan["thresholds"] == full["thresholds"]
    assert not any(k in plan["reproduction"] for k in demo.RESULT_FIELDS)
    assert plan["reproduction"]["n"] == full["reproduction"]["n"]  # the planned n stays


def test_same_record_in_one_commit_is_post_hoc(examples_dir, git_repo):
    dst = git_repo.root / "reproduction" / "committed_first.yaml"
    dst.parent.mkdir(parents=True)
    shutil.copy(examples_dir / "records" / "committed_first.yaml", dst)
    git_repo.commit("plan and result together")
    rep = check_file(dst, repo=git_repo.root, backend="fallback")
    assert rep.extra["verdict"]["commit_order"] == "thresholds_post_hoc(same_commit)"
    assert rep.exit_code() == 1
