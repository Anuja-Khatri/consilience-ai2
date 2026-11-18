"""v0.2 DiscoveryBench additions (``analyses/reproduce/discoverybench_planted.py``): the
fixed binning and mutual information, the permutation test, Spearman's rho and the rule
that derives planted pairs from column names in a prose gold hypothesis. Synthetic data."""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ANALYSES = Path(__file__).resolve().parents[2] / "analyses" / "reproduce"
if str(ANALYSES) not in sys.path:
    sys.path.insert(0, str(ANALYSES))
db = importlib.import_module("discoverybench_planted")


def test_mi_codes_by_value_and_by_quartile():
    assert db.mi_codes(np.array([0.0, 1.0, 1.0, 0.0])).tolist() == [0, 1, 1, 0]
    x = np.arange(8, dtype=float)
    assert db.mi_codes(x).tolist() == [0, 0, 1, 1, 2, 2, 3, 3]


def test_mutual_information_values():
    a = np.array([0, 0, 1, 1])
    assert db.mutual_information(a, a) == pytest.approx(math.log(2))
    assert db.mutual_information(a, np.array([0, 1, 0, 1])) == pytest.approx(0.0)


def test_mi_test_detects_non_monotone_dependence_and_is_deterministic():
    rng = np.random.default_rng(1)
    x = rng.uniform(-1, 1, 200)
    y = x ** 2 + rng.normal(0, 0.05, 200)       # no linear or monotone trend
    mi, p = db.mi_test(x, y, "t:y:x")
    assert p == pytest.approx(1 / (1 + db.MI_PERMUTATIONS)) and mi > 0.3
    assert db.mi_test(x, y, "t:y:x") == (mi, p)
    assert db._r(x, y)[1] > 0.05                # Pearson misses it
    _, p_null = db.mi_test(x, rng.uniform(size=200), "t:z:x")
    assert p_null > 0.05


def test_rho_is_rank_based_and_refuses_constants():
    x = np.arange(1, 21, dtype=float)
    rho, p = db._rho(x, np.exp(x))
    assert rho == pytest.approx(0.999999) and p < 1e-6
    assert db._rho(x, np.ones(20)) is None


@pytest.mark.parametrize("text,named", [
    ("The shape_index depends on preventive measures.", ["shape_index", "preventive_measures"]),
    ("Higher Shape Index with more stages", ["shape_index"]),
    ("the stage of the structure", []),                 # "age" is not a whole word here
    ("age and shape_index_v2 matter", ["age"]),          # a longer name does not match
])
def test_named_columns(text, named):
    cols = ["shape_index", "preventive_measures", "age"]
    assert db.named_columns(text, cols) == named
