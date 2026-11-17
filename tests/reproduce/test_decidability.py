"""D1 decidability: every class, and the power formulas against reference values."""

from __future__ import annotations

import pytest

from consilience_ai2.reproduce import check_decidability, evaluate, parse
from consilience_ai2.reproduce.stats import (
    PowerError,
    equivalence_power,
    interval,
    p_from_effect,
    power,
    se_from,
)


@pytest.mark.parametrize("args,expected", [
    # reference values (G*Power-style exact noncentral t; Fisher z for r; arcsine for h)
    (("d", 0.5, 128, 0.05, 2), 0.8015),   # 64 per group
    (("d", 0.5, 102, 0.05, 1), 0.8059),   # one-sided
    (("dz", 0.5, 34, 0.05, 2), 0.8078),
    (("r", 0.3, 85, 0.05, 2), 0.8003),
    (("h", 0.2, 786, 0.05, 2), 0.8006),   # 393 per group
])
def test_power_reference_values(args, expected):
    assert power(*args) == pytest.approx(expected, abs=5e-4)


def test_power_uses_magnitude_and_groups():
    assert power("r", -0.3, 85, 0.05, 2) == power("r", 0.3, 85, 0.05, 2)
    assert power("d", 0.5, 128, 0.05, 2, (32, 96)) < power("d", 0.5, 128, 0.05, 2)


@pytest.mark.parametrize("args,msg", [
    (("r", 0.3, 3, 0.05, 2), "n > 3"),
    (("r", 1.0, 30, 0.05, 2), "below 1"),
    (("d", 0.5, 3, 0.05, 2), "2 cases per group"),
    (("dz", 0.5, 1, 0.05, 2), "n >= 2"),
    (("h", 0.2, 1, 0.05, 2), "non-empty"),
    (("odds", 1.2, 100, 0.05, 2), "no power formula"),
    (("d", 0.5, 100, 0.05, 2, (10, 10)), "does not add up"),
])
def test_power_errors(args, msg):
    with pytest.raises(PowerError, match=msg):
        power(*args)


def test_p_from_effect():
    assert p_from_effect("r", 0.27, 180, 2, 1) == pytest.approx(0.000247, rel=1e-2)
    two = p_from_effect("dz", 0.3, 40, 2, 1)
    assert p_from_effect("dz", 0.3, 40, 1, 1) == pytest.approx(two / 2)
    assert p_from_effect("dz", 0.3, 40, 1, -1) > 0.9      # wrong direction, one-sided
    assert 0 < p_from_effect("h", 0.2, 200, 2, 1) < 1
    assert 0 < p_from_effect("d", 0.4, 60, 2, 1) < 1


def test_equivalence_power_and_interval():
    assert equivalence_power(0.01, 0.0021, 0.05) == pytest.approx(0.998, abs=1e-3)
    assert equivalence_power(0.01, 0.02, 0.05) == 0.0
    with pytest.raises(PowerError):
        equivalence_power(0.01, 0, 0.05)
    assert se_from((0.0, 3.92), 0.95, None) == pytest.approx(1.0, abs=1e-3)
    assert se_from(None, None, None) is None
    lo, hi = interval(10.0, ci=None, ci_level=None, se=1.0, alpha=0.05)
    assert (lo, hi) == pytest.approx((8.355, 11.645), abs=1e-3)
    assert interval(1.0, ci=None, ci_level=None, se=None, alpha=0.05) is None


def d1(rec):
    return check_decidability(parse(rec))


def test_decidable(record):
    r = d1(record())
    assert r.cls == "decidable" and r.power > 0.8


def test_underpowered(record):
    r = d1(record(reproduction={"n": 30}))
    assert r.cls == "underpowered" and "below 0.8" in r.reason


def test_power_threshold_is_configurable(record):
    assert d1(record(reproduction={"n": 60}, thresholds={"power": 0.5})).cls == "decidable"
    assert d1(record(reproduction={"n": 60}, thresholds={"power": 0.95})).cls == "underpowered"


@pytest.mark.parametrize("over", [
    {"reproduction": {"status": "no_data"}},
    {"reproduction": {"status": "not_run"}},
    {"reproduction": {"n": 0}},
])
def test_no_data(record, over):
    assert d1(record(over)).cls == "no_data"


def test_no_data_when_no_result_numbers(record):
    rec = record()
    for k in ("value", "p", "effect_size"):
        del rec["reproduction"][k]
    assert d1(rec).cls == "no_data"


def test_not_identifiable(record):
    r = d1(record(identifiability={"identifiable": False, "reason": "true by construction"}))
    assert (r.cls, r.reason) == ("not_identifiable", "true by construction")


@pytest.mark.parametrize("over,why", [
    ({"source": {"effect_size": {"value": 0}}}, "zero"),
    ({"thresholds": {"alpha": "0,05"}}, "alpha"),
    ({"thresholds": {"power": 2}}, "power threshold"),
    ({"source": {"effect_size": {"type": "r", "value": 0.3}},
      "reproduction": {"n": 3}}, "n > 3"),
])
def test_uncheckable(record, over, why):
    r = d1(record(over))
    assert r.cls == "uncheckable" and why in r.reason


def test_uncheckable_without_reproduction_n(record):
    rec = record()
    del rec["reproduction"]["n"]
    assert d1(rec).reason == "no reproduction n"


def test_uncheckable_without_source_effect(record):
    rec = record()
    del rec["source"]["effect_size"]
    assert "no source effect" in d1(rec).reason


def equiv(record, **rep):
    return record({"thresholds": {"minimum_effect": None, "equivalence_margin": 0.01}},
                  source={"value": 0.512, "unit": "V", "effect_size": None},
                  reproduction={"value": 0.509, "unit": "V", "effect_size": None, "p": None,
                                **rep})


def _clean(rec):
    for side in ("source", "reproduction"):
        for k in [k for k, v in rec[side].items() if v is None]:
            del rec[side][k]
    rec["thresholds"] = {k: v for k, v in rec["thresholds"].items() if v is not None}
    return rec


def test_equivalence_decidability(record):
    assert d1(_clean(equiv(record, se=0.0021))).cls == "decidable"
    assert d1(_clean(equiv(record, se=0.02))).cls == "underpowered"
    assert d1(_clean(equiv(record, ci=[0.505, 0.513]))).cls == "decidable"
    assert "no reproduction se or ci" in d1(_clean(equiv(record))).reason


def test_d1_severity(record):
    rep = evaluate(record(reproduction={"n": 30}), backend="fallback", skip=("P1",))
    f = next(x for x in rep.findings if x.code == "D1")
    assert f.severity == "warning" and f.details["decidability"] == "underpowered"
    rep = evaluate(record(), backend="fallback", skip=("P1",))
    assert next(x for x in rep.findings if x.code == "D1").severity == "info"
