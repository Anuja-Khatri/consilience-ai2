"""BH against a published reference result, and the power formulas."""

from __future__ import annotations

import math

import pytest

from consilience_ai2.audit import stats

# Benjamini and Hochberg (1995), J. R. Statist. Soc. B 57(1), section 4.1: 15 p values
# from a clinical trial; at q = 0.05 the procedure rejects the four smallest.
BH1995 = [0.0001, 0.0004, 0.0019, 0.0095, 0.0201, 0.0278, 0.0298, 0.0344, 0.0459, 0.3240,
          0.4262, 0.5719, 0.6528, 0.7590, 1.0000]


def test_bh_reference_rejections():
    assert stats.bh_rejections(BH1995, 0.05) == 4


def test_bh_reference_adjusted_values():
    q = stats.benjamini_hochberg(BH1995)
    # step-up adjusted values computed by hand: q_(i) = min_{j>=i} m p_(j) / j
    expected = [0.0015, 0.003, 0.0095, 0.035625, 0.0603, 0.06385714, 0.06385714, 0.0645,
                0.0765, 0.486, 0.58118182, 0.71487500, 0.75323077, 0.81321429, 1.0]
    assert q == pytest.approx(expected, rel=1e-6)


def test_bh_matches_scipy():
    scipy_stats = pytest.importorskip("scipy.stats")
    if not hasattr(scipy_stats, "false_discovery_control"):
        pytest.skip("scipy < 1.11")
    ps = [0.01, 0.04, 0.03, 0.5, 0.2, 0.001, 0.049, 0.9]
    ref = scipy_stats.false_discovery_control(ps, method="bh")
    assert stats.benjamini_hochberg(ps) == pytest.approx(list(ref))


def test_bh_input_order_monotone_and_capped():
    ps = [0.9, 0.01, 0.5, 0.02]
    q = stats.benjamini_hochberg(ps)
    assert q[1] <= q[3] <= q[2] <= q[0] <= 1.0
    assert stats.benjamini_hochberg([]) == []
    with pytest.raises(ValueError):
        stats.benjamini_hochberg([1.2])


def test_power_formulas():
    assert stats.n_floor(0.8) == 25
    assert stats.R3_N_FLOOR == 25
    assert stats.mde_d(64) == pytest.approx(0.4952, abs=1e-3)
    assert stats.mde_r(100) == pytest.approx(0.2765, abs=1e-3)
    assert stats.mde_d(1) == math.inf
