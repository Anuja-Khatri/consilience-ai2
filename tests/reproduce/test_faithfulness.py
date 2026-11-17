"""F1 faithfulness: every class and every not_comparable cause, on both backends."""

from __future__ import annotations

import pytest

from consilience_ai2.reproduce import check_faithfulness, consilience_version, evaluate, parse
from consilience_ai2.reproduce.comparability import convert, resolve_backend

HAVE_CONS = consilience_version() is not None
BACKENDS = ["fallback", pytest.param("consilience", marks=pytest.mark.skipif(
    not HAVE_CONS, reason="consilience not installed"))]


def f1(rec, backend, pack=None):
    return check_faithfulness(parse(rec), backend, pack)


@pytest.mark.parametrize("backend", BACKENDS)
def test_same_quantity(record, backend):
    r = f1(record(), backend)
    assert (r.cls, r.label, r.mismatches) == ("same_quantity", "same_quantity", [])
    assert r.backend.startswith("consilience" if backend == "consilience" else "fallback")


@pytest.mark.parametrize("backend", BACKENDS)
def test_same_quantity_without_declared_mapping(record, delete, backend):
    assert f1(record(quantity_mapping=delete), backend).cls == "same_quantity"


@pytest.mark.parametrize("backend", BACKENDS)
def test_proxy_is_a_caveat(record, backend):
    r = f1(record(reproduction={"quantity": "Spearman rho between sleep and recall"},
                  quantity_mapping={"relation": "proxy", "note": "rank stands in for r"}),
           backend)
    assert r.cls == "proxy" and r.caveats == ["proxy: rank stands in for r"]


@pytest.mark.parametrize("backend", BACKENDS)
def test_substitution(record, backend):
    r = f1(record(quantity_mapping={"relation": "substitution"}), backend)
    assert r.cls == "substitution"


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("over,target", [
    ({"reproduction": {"quantity": "Spearman rho"}}, "quantity"),
    ({"quantity_mapping": None, "reproduction": {"quantity": "Spearman rho"}},
     "quantity_mapping"),
    ({"reproduction": {"effect_size": {"type": "d"}}}, "effect_size.type"),
    ({"reproduction": {"unit": ""}}, "reproduction.unit"),
    ({"reproduction": {"conditions": {"method": "Spearman"}}}, "conditions.method"),
    ({"reproduction": {"conditions": {"method": None, "extra": "x"}}}, "conditions.extra"),
    ({"reproduction": {"conditions": {"cohort": "A"}}}, "conditions.cohort"),
    ({"reproduction": {"value": "0,27"}}, "reproduction.value"),
])
def test_not_comparable(record, backend, over, target):
    rec = record(over)
    if over.get("quantity_mapping", 0) is None:
        del rec["quantity_mapping"]
    r = f1(rec, backend)
    assert r.cls == "not_comparable", r.mismatches
    assert target in {m["target"] for m in r.mismatches}, r.mismatches
    assert r.label.startswith("not_comparable(") and target in r.label


@pytest.mark.parametrize("backend", BACKENDS)
def test_independence_axis_must_be_stated(record, backend):
    rec = record()
    del rec["reproduction"]["conditions"]["cohort"]
    r = f1(rec, backend)
    assert {"target": "conditions.cohort", "reason": "not_stated",
            "detail": "the independence axis must be stated on both sides"} in r.mismatches


@pytest.mark.parametrize("backend", BACKENDS)
def test_no_axis_means_every_condition_must_match(record, delete, backend):
    r = f1(record(independence_axis=delete), backend)
    assert r.cls == "not_comparable" and "conditions.cohort" in r.label


@pytest.mark.parametrize("backend", BACKENDS)
def test_effect_size_on_one_side(record, backend):
    rec = record()
    del rec["reproduction"]["effect_size"]
    assert "effect_size" in f1(rec, backend).label


def test_fallback_units_by_name(record):
    r = f1(record(source={"unit": "V", "value": 0.5}, reproduction={"unit": "mV", "value": 500}),
           "fallback")
    assert r.cls == "not_comparable" and "unit" in r.label
    ok = f1(record(source={"unit": "%", "value": 31}, reproduction={"unit": "dimensionless",
                                                                    "value": 0.27}), "fallback")
    assert ok.cls == "same_quantity"
    assert convert(31, "percent", "dimensionless", "fallback") == pytest.approx(0.31)
    with pytest.raises(ValueError):
        convert(1, "V", "mV", "fallback")


def test_fallback_refuses_a_pack(record):
    r = f1(record(conditions_pack="electrochemistry"), "fallback")
    assert "conditions_pack" in r.label


def test_yaml_dates_stay_text_and_date_objects_are_refused(record):
    import datetime

    from consilience_ai2.reproduce.record import parse_text

    assert parse_text("time: 2026-01-01\n") == {"time": "2026-01-01"}
    rep = evaluate(record(reproduction={"conditions": {"method": datetime.date(2026, 1, 1)}}))
    assert [f.code for f in rep.findings] == ["S1"]


def test_fallback_unsupported_condition_type(record):
    rec = parse(record(reproduction={"conditions": {"method": {1, 2}}}), file_sha256="0" * 64)
    r = check_faithfulness(rec, "fallback")
    assert "conditions.method" in r.label


@pytest.mark.skipif(not HAVE_CONS, reason="consilience not installed")
def test_consilience_converts_units_and_quantities(record):
    r = f1(record(source={"unit": "V", "value": 0.5}, reproduction={"unit": "mV", "value": 500}),
           "consilience")
    assert r.cls == "same_quantity"
    r = f1(record(source={"unit": "V"}, reproduction={"unit": "s"}), "consilience")
    assert r.cls == "not_comparable" and "unit" in r.label
    assert convert(500, "mV", "V", "consilience") == pytest.approx(0.5)
    # a condition with a unit is compared as a quantity, after conversion
    r = f1(record(source={"conditions": {"temperature": "25 degC"}},
                  reproduction={"conditions": {"temperature": "298.15 K"}}), "consilience")
    assert r.cls == "same_quantity"


@pytest.mark.skipif(not HAVE_CONS, reason="consilience not installed")
def test_consilience_pack(record):
    r = f1(record(conditions_pack="electrochemistry"), "consilience")
    assert r.backend.startswith("consilience")


def test_resolve_backend(monkeypatch):
    import consilience_ai2.reproduce.comparability as c

    monkeypatch.setattr(c, "consilience_version", lambda: None)
    assert resolve_backend("auto") == "fallback"
    with pytest.raises(ValueError, match="not installed"):
        resolve_backend("consilience")
    with pytest.raises(ValueError):
        resolve_backend("other")


@pytest.mark.parametrize("cls,severity", [("same_quantity", "info"), ("proxy", "warning"),
                                          ("substitution", "error"),
                                          ("not_comparable", "error")])
def test_f1_severity(record, cls, severity):
    over = {"same_quantity": {}, "proxy": {"quantity_mapping": {"relation": "proxy"}},
            "substitution": {"quantity_mapping": {"relation": "substitution"}},
            "not_comparable": {"reproduction": {"conditions": {"method": "OLS"}}}}[cls]
    rep = evaluate(record(over), backend="fallback", skip=("P1",))
    f = next(x for x in rep.findings if x.code == "F1")
    assert (f.details["class"], f.severity) == (cls, severity)
    assert f.receipt is not None and len(f.receipt.sha256) == 64
