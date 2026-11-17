"""P1 commit order on a scratch git repository: every outcome and reason."""

from __future__ import annotations

import pytest

from consilience_ai2.reproduce import check_commit_order, check_file


@pytest.fixture
def pre(record):
    """The record before the run: thresholds committed, no result numbers yet."""
    rec = record()
    for k in ("value", "p", "effect_size"):
        del rec["reproduction"][k]
    return rec


def p1(path, repo=None):
    from consilience_ai2.reproduce import load_file

    return check_commit_order(load_file(path), path, repo)


# -------------------------------------------------------------- by the file's history
def test_history_thresholds_first(git_repo, pre, record):
    git_repo.write("rec.yaml", pre)
    t = git_repo.commit("design")
    git_repo.write("rec.yaml", record())
    r = git_repo.commit("result")
    out = p1(git_repo.root / "rec.yaml")
    assert out.cls == "committed_first" and out.method == "git log of the record file"
    assert (out.details["thresholds_commit"], out.details["result_commit"]) == (t, r)


def test_history_same_commit(git_repo, record):
    git_repo.write("rec.yaml", record())
    git_repo.commit("all at once")
    out = p1(git_repo.root / "rec.yaml")
    assert (out.cls, out.reason, out.proven) == ("thresholds_post_hoc", "same_commit", True)


def test_history_thresholds_set_after_result(git_repo, pre, record):
    git_repo.write("rec.yaml", record(thresholds={"minimum_effect": 0.3}))
    git_repo.commit("result with a loose threshold")
    git_repo.write("rec.yaml", record())
    git_repo.commit("threshold moved")
    out = p1(git_repo.root / "rec.yaml")
    assert (out.cls, out.reason) == ("thresholds_post_hoc", "after_result")


def test_history_changed_after_result(git_repo, pre, record):
    git_repo.write("rec.yaml", pre)
    git_repo.commit("design")
    git_repo.write("rec.yaml", record(thresholds={"alpha": 0.1}))
    git_repo.commit("result, alpha loosened")
    git_repo.write("rec.yaml", record())
    git_repo.commit("alpha put back")
    out = p1(git_repo.root / "rec.yaml")
    assert (out.cls, out.reason) == ("thresholds_post_hoc", "changed_after_result")
    assert len(out.details["changed_in"]) == 1


def test_history_adding_commit_refs_does_not_count_as_a_change(git_repo, pre, record):
    git_repo.write("rec.yaml", pre)
    git_repo.commit("design")
    git_repo.write("rec.yaml", record())
    git_repo.commit("result")
    git_repo.write("rec.yaml", record(thresholds={"committed": {"time": "2026-01-01"}}))
    git_repo.commit("note the time")
    assert p1(git_repo.root / "rec.yaml").cls == "committed_first"


@pytest.mark.parametrize("case,why", [
    ("untracked", "no committed history"),
    ("result_uncommitted", "the result is not committed"),
    ("thresholds_uncommitted", "the current thresholds are not committed"),
])
def test_history_not_shown(git_repo, pre, record, case, why):
    if case == "untracked":
        git_repo.commit("empty")
        git_repo.write("rec.yaml", record())
    elif case == "result_uncommitted":
        git_repo.write("rec.yaml", pre)
        git_repo.commit("design")
        git_repo.write("rec.yaml", record())
    else:
        git_repo.write("rec.yaml", pre)
        git_repo.commit("design")
        git_repo.write("rec.yaml", record())
        git_repo.commit("result")
        git_repo.write("rec.yaml", record(thresholds={"alpha": 0.01}))
    out = p1(git_repo.root / "rec.yaml")
    assert (out.cls, out.reason, out.proven) == ("thresholds_post_hoc", "not_shown", False)
    assert why in out.details["why"]


def test_unparseable_old_version_is_counted(git_repo, pre, record):
    (git_repo.root / "rec.yaml").write_text("id: [unclosed\n", encoding="utf-8")
    git_repo.commit("broken")
    git_repo.write("rec.yaml", pre)
    git_repo.commit("design")
    git_repo.write("rec.yaml", record())
    git_repo.commit("result")
    out = p1(git_repo.root / "rec.yaml")
    assert out.cls == "committed_first" and out.details["unparsed_versions"] == 1


# ------------------------------------------------------------------ by declared refs
def _refs(git_repo, record, t, r):
    rec = record(thresholds={"committed": {"commit": t, "time": "2026-01-01T00:00:00Z"}},
                 result_committed={"commit": r})
    git_repo.write("declared.yaml", rec)
    return git_repo.root / "declared.yaml"


def test_refs_thresholds_first(git_repo, record):
    t = git_repo.commit("design")
    r = git_repo.commit("result")
    out = p1(_refs(git_repo, record, t, r))
    assert out.cls == "committed_first" and out.method == "declared commit refs"
    assert out.details["thresholds_commit_time"] < out.details["result_commit_time"]
    assert out.details["declared_thresholds_time"] == "2026-01-01T00:00:00Z"


def test_refs_same_commit(git_repo, record):
    c = git_repo.commit("both")
    assert p1(_refs(git_repo, record, c, c)).reason == "same_commit"


def test_refs_after_result(git_repo, record):
    r = git_repo.commit("result")
    t = git_repo.commit("design")
    out = p1(_refs(git_repo, record, t, r))
    assert (out.cls, out.reason, out.proven) == ("thresholds_post_hoc", "after_result", True)


def test_refs_not_found(git_repo, record):
    r = git_repo.commit("result")
    out = p1(_refs(git_repo, record, "deadbeefdeadbeef", r))
    assert out.reason == "not_shown" and "thresholds" in out.details["why"]


def test_refs_unrelated_histories(git_repo, record):
    base = git_repo.commit("base")
    git_repo.run("checkout", "-q", "--orphan", "other")
    t = git_repo.commit("design on another root")
    git_repo.run("checkout", "-q", base)
    git_repo.run("checkout", "-q", "-b", "main2")
    r = git_repo.commit("result")
    out = p1(_refs(git_repo, record, t, r))
    assert out.reason == "not_shown" and "unrelated" in out.details["why"]


def test_refs_with_explicit_repo(git_repo, record, tmp_path):
    t = git_repo.commit("design")
    r = git_repo.commit("result")
    rec = record(thresholds={"committed": {"commit": t}}, result_committed={"commit": r})
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    path = outside / "rec.yaml"
    import yaml

    path.write_text(yaml.safe_dump(rec), encoding="utf-8")
    assert p1(path).details["why"].startswith("no git repository")
    assert p1(path, git_repo.root).cls == "committed_first"


# ----------------------------------------------------------------------- the rest
def test_not_applicable_without_result(git_repo, pre):
    git_repo.write("rec.yaml", pre)
    git_repo.commit("design")
    out = p1(git_repo.root / "rec.yaml")
    assert out.cls == "not_applicable"


def test_no_record_file_and_no_refs(record, git_repo):
    git_repo.commit("x")
    out = check_commit_order(record(), None, git_repo.root)
    assert out.reason == "not_shown" and "no record file" in out.details["why"]


def test_record_outside_repo(git_repo, record, tmp_path):
    git_repo.commit("x")
    other = tmp_path / "o.yaml"
    import yaml

    other.write_text(yaml.safe_dump(record()), encoding="utf-8")
    out = check_commit_order(record(), other, git_repo.root)
    assert "outside the repository" in out.details["why"]


@pytest.mark.parametrize("setup,severity", [("first", "info"), ("same", "error"),
                                            ("untracked", "warning")])
def test_p1_severity(git_repo, pre, record, setup, severity):
    if setup == "first":
        git_repo.write("rec.yaml", pre)
        git_repo.commit("design")
        git_repo.write("rec.yaml", record())
        git_repo.commit("result")
    elif setup == "same":
        git_repo.write("rec.yaml", record())
        git_repo.commit("all")
    else:
        git_repo.commit("empty")
        git_repo.write("rec.yaml", record())
    rep = check_file(git_repo.root / "rec.yaml", backend="fallback")
    f = next(x for x in rep.findings if x.code == "P1")
    assert f.severity == severity
    assert rep.exit_code() == (1 if severity == "error" else 0)
