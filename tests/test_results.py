import json

import pytest

from consilience_ai2.core.results import (
    ResultsError,
    build_registry,
    load_results,
    metric,
    metrics_sha256,
    validate_metric,
    write_registry,
    write_results,
)


def m(mid, value=0.5, **kw):
    base = dict(n=10, source="fetch:x", dev_or_heldout="descriptive")
    base.update(kw)
    return metric(mid, value, **base)


def test_metric_builder_and_fields():
    rec = m("receipts.t1_rate", 0.1, ci_lo=0.05, ci_hi=0.2, caveats=["c"], unit="rate")
    assert rec == {"metric_id": "receipts.t1_rate", "value": 0.1, "n": 10, "ci_lo": 0.05,
                   "ci_hi": 0.2, "source": "fetch:x", "caveats": ["c"],
                   "dev_or_heldout": "descriptive", "unit": "rate"}


@pytest.mark.parametrize("kw", [
    {"value": True},
    {"value": float("nan")},
    {"value": None},                         # None needs a caveat
    {"n": -1},
    {"n": 1.5},
    {"ci_lo": 0.1},                          # only one bound
    {"ci_lo": 0.3, "ci_hi": 0.1},
    {"source": " "},
    {"dev_or_heldout": "test"},
    {"caveats": "one string"},
    {"colour": "red"},                       # unknown field
])
def test_metric_validation(kw):
    value = kw.pop("value", 0.5)
    base = dict(n=10, source="fetch:x", dev_or_heldout="dev")
    base.update(kw)
    with pytest.raises(ResultsError):
        metric("audit.x", value, **base)


def test_value_none_with_caveat_is_allowed():
    assert m("audit.r5", None, caveats=["not implemented"])["value"] is None


def test_metric_id_must_carry_component_prefix():
    with pytest.raises(ResultsError):
        validate_metric(m("audit.x"), "receipts")
    with pytest.raises(ResultsError):
        m("audit.Bad Name")


def test_write_results_is_deterministic(tmp_path):
    recs = [m("audit.b"), m("audit.a", 1)]
    p1 = write_results("audit", recs, tmp_path)
    t1 = p1.read_text()
    p2 = write_results("audit", list(reversed(recs)), tmp_path)
    assert p2.read_text() == t1
    data = json.loads(t1)
    assert [x["metric_id"] for x in data["metrics"]] == ["audit.a", "audit.b"]
    assert load_results(p1)["component"] == "audit"


def test_write_results_refuses_duplicates_and_bad_names(tmp_path):
    with pytest.raises(ResultsError):
        write_results("audit", [m("audit.a"), m("audit.a")], tmp_path)
    with pytest.raises(ResultsError):
        write_results("Audit", [], tmp_path)


def test_build_registry_merges_and_skips_registry_and_lock(tmp_path):
    write_results("receipts", [m("receipts.x", 0.25)], tmp_path)
    write_results("audit", [m("audit.y", 3)], tmp_path)
    (tmp_path / "registry.json").write_text('{"stale": true}')
    (tmp_path / "NUMBERS_LOCK.json").write_text("{}")
    reg = build_registry(tmp_path)
    assert [x["metric_id"] for x in reg["metrics"]] == ["audit.y", "receipts.x"]
    assert set(reg["components"]) == {"audit", "receipts"}
    assert reg["components"]["audit"]["n_metrics"] == 1
    assert reg["metrics_sha256"] == metrics_sha256(reg["metrics"])
    path = write_registry(tmp_path)
    assert json.loads(path.read_text())["metrics"] == reg["metrics"]
    assert write_registry(tmp_path).read_text() == path.read_text()  # idempotent


def test_build_registry_refuses_cross_file_duplicates(tmp_path):
    write_results("audit", [m("audit.y")], tmp_path)
    # a hand-edited file claiming another component's id
    bad = {"schema_version": 1, "component": "receipts",
           "metrics": [dict(m("audit.y"))]}
    (tmp_path / "receipts.json").write_text(json.dumps(bad))
    with pytest.raises(ResultsError):
        build_registry(tmp_path)


def test_load_results_checks_component_matches_file(tmp_path):
    (tmp_path / "audit.json").write_text(json.dumps(
        {"schema_version": 1, "component": "receipts", "metrics": []}))
    with pytest.raises(ResultsError):
        load_results(tmp_path / "audit.json")


def test_empty_registry(tmp_path):
    reg = build_registry(tmp_path)
    assert reg["metrics"] == [] and reg["components"] == {}
