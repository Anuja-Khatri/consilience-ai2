"""Record loading: schema (S1), duplicate keys, fail-closed number reading."""

from __future__ import annotations

import json

import pytest

from consilience_ai2.reproduce import RecordError, evaluate, parse, schema, validate
from consilience_ai2.reproduce.record import parse_text, read_count, read_number


def test_schema_is_valid_json_with_id():
    s = schema()
    assert s["$id"] == "consilience-ai2/reproduction-record/1"
    assert "source" in s["required"] and "thresholds" in s["required"]


def test_base_record_is_valid(record):
    assert validate(record()) == []


def test_every_example_record_is_valid(examples_dir):
    from consilience_ai2.reproduce import load_file

    paths = sorted((examples_dir / "records").glob("*.yaml"))
    assert len(paths) >= 5
    for p in paths:
        assert validate(load_file(p)) == [], p.name


@pytest.mark.parametrize("over,needle", [
    ({"surprise": 1}, "unknown field 'surprise'"),
    ({"schema_version": 2}, "schema_version: must be 1"),
    ({"thresholds": {"equivalence_margin": 0.1}}, "exactly one of"),
    ({"source": {"effect_size": {"type": "odds"}}}, "must be one of"),
    ({"quantity_mapping": {"relation": "similar"}}, "must be one of"),
    ({"reproduction": {"n": True}}, "expected integer or string"),
    ({"thresholds": {"sides": 3}}, "must be one of"),
])
def test_schema_errors(record, over, needle):
    errs = validate(record(over))
    assert any(needle in e for e in errs), errs


def test_missing_required(record, delete):
    assert any("missing required field 'thresholds'" in e
               for e in validate(record(thresholds=delete)))


def test_s1_is_an_error_and_nothing_else_runs(record):
    rep = evaluate(record(surprise=1))
    assert [f.code for f in rep.findings] == ["S1"]
    assert rep.exit_code() == 1 and rep.extra["verdict"] is None


def test_duplicate_keys_refused():
    with pytest.raises(RecordError, match="duplicate key"):
        parse_text("id: a\nid: b\n")
    with pytest.raises(RecordError, match="duplicate key"):
        parse_text('{"id": "a", "id": "b"}')


def test_not_a_mapping():
    with pytest.raises(RecordError, match="mapping"):
        parse_text("- 1\n- 2\n")


@pytest.mark.parametrize("raw,value,why", [
    (0.25, 0.25, None),
    (3, 3.0, None),
    ("0.25", 0.25, None),
    ("1.5e-3", 0.0015, None),
    (" -0.3 ", -0.3, None),
    ("1,234", 1234.0, None),
    ("1,2", None, "ambiguous_separators"),
    ("1.234,5", None, "ambiguous_separators"),
    ("31%", None, "percent_sign: write the unit in 'unit'"),
    ("0.3 V", None, "extra_text"),
    ("about 0.3", None, "extra_text"),
    ("0.3 or 0.4", None, "not_one_number"),
    ("n/a", None, "no_number"),
    ("", None, "empty"),
    ("nan", None, "non_finite"),
    (float("inf"), None, "non_finite"),
    (True, None, "boolean_not_number"),
    ([1], None, "not_a_number (list)"),
])
def test_read_number_fail_closed(raw, value, why):
    v, w = read_number(raw)
    assert (v, w) == (value, why)


def test_read_count():
    assert read_count(12) == (12, None)
    assert read_count("1,200") == (1200, None)
    assert read_count(2.5) == (None, "not_a_count")
    assert read_count(-1) == (None, "not_a_count")


def test_unreadable_numbers_are_listed_not_raised(record):
    p = parse(record(reproduction={"value": "0,27", "p": 1.5}, thresholds={"alpha": 2}))
    fields = {(u.field, u.reason) for u in p.unreadable}
    assert ("reproduction.value", "ambiguous_separators") in fields
    assert ("reproduction.p", "not_a_probability") in fields
    assert ("thresholds.alpha", "not_in_(0,1)") in fields


def test_proportions_become_cohens_h(record):
    p = parse(record(source={"effect_size": {"type": "proportions", "p1": 0.6, "p2": 0.4}},
                     reproduction={"effect_size": {"type": "proportions", "p1": 0.5,
                                                   "p2": 0.5}}))
    assert p.source.effect.type == "h"
    assert p.source.effect.value == pytest.approx(0.4027, abs=1e-4)
    assert p.reproduction.effect.value == 0
    bad = parse(record(source={"effect_size": {"type": "proportions", "p1": 1.2, "p2": 0.4}}))
    assert any(u.field == "source.effect_size" for u in bad.unreadable)


def test_json_records_load(tmp_path, record):
    from consilience_ai2.reproduce import check_file

    f = tmp_path / "r.json"
    f.write_text(json.dumps(record()), encoding="utf-8")
    rep = check_file(f, skip=("P1",))
    assert rep.extra["verdict"]["verdict"] == "reproduced"


def test_unreadable_file(tmp_path):
    from consilience_ai2.reproduce import check_file

    f = tmp_path / "bad.yaml"
    f.write_bytes(b"\xff\xfe not utf-8")
    rep = check_file(f)
    assert [x.code for x in rep.findings] == ["S1"]
    assert rep.exit_code() == 1
