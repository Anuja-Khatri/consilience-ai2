"""The statistics the audit uses, in closed form. No randomness, no model calls.

- ``benjamini_hochberg(pvalues)``: BH step-up adjusted q values (Benjamini and Hochberg,
  1995), returned in input order. ``q_(i) = min_{j >= i} min(1, m * p_(j) / j)`` over the
  sorted p values, so q is monotone in p and never above 1.
- ``mde_d(n_per_group)``: the minimum detectable standardised mean difference (Cohen's d)
  for a two-sided two-sample z approximation at ``ALPHA`` and ``POWER``:
  ``d = (z_{1-alpha/2} + z_{power}) * sqrt(2 / n)``.
- ``mde_r(n)``: the minimum detectable correlation by the Fisher z approximation:
  ``r = tanh((z_{1-alpha/2} + z_{power}) / sqrt(n - 3))``.
- ``n_floor(d)``: the smallest per-group n that reaches ``POWER`` for effect ``d``
  (``ceil(2 * ((z_{1-alpha/2} + z_{power}) / d) ** 2)``).

The constants are fixed and documented in docs/audit.md: alpha 0.05 two-sided, power
0.80, the R3 floor at a large effect (d = 0.8) and the A6 "underpowered null" bound at a
medium effect (d = 0.5), after Cohen (1988).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from scipy.stats import norm

ALPHA = 0.05
POWER = 0.80
R3_EFFECT_D = 0.8   # R3: the floor is the n needed to detect a large effect
A6_MAX_MDE_D = 0.5  # A6: a null is "underpowered" when it could not detect a medium effect
Q_THRESHOLD = 0.05  # A5: surprising nodes with q above this are flagged


def _z_sum(alpha: float = ALPHA, power: float = POWER) -> float:
    return float(norm.ppf(1 - alpha / 2) + norm.ppf(power))


def benjamini_hochberg(pvalues: Sequence[float]) -> list[float]:
    """BH-adjusted q values, in the order given. Empty input gives an empty list."""
    m = len(pvalues)
    if m == 0:
        return []
    for p in pvalues:
        if not (0.0 <= p <= 1.0) or math.isnan(p):
            raise ValueError(f"p value out of [0, 1]: {p!r}")
    order = sorted(range(m), key=lambda i: (pvalues[i], i))
    q = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, pvalues[i] * m / rank)
        q[i] = min(1.0, running)
    return q


def bh_rejections(pvalues: Sequence[float], q: float = Q_THRESHOLD) -> int:
    """How many hypotheses BH rejects at level ``q``."""
    return sum(1 for v in benjamini_hochberg(pvalues) if v <= q)


def mde_d(n_per_group: int, alpha: float = ALPHA, power: float = POWER) -> float:
    """Minimum detectable Cohen's d for two groups of ``n_per_group`` each."""
    if n_per_group < 2:
        return math.inf
    return _z_sum(alpha, power) * math.sqrt(2.0 / n_per_group)


def mde_r(n: int, alpha: float = ALPHA, power: float = POWER) -> float:
    """Minimum detectable Pearson r with ``n`` pairs (Fisher z)."""
    if n <= 3:
        return 1.0
    return math.tanh(_z_sum(alpha, power) / math.sqrt(n - 3))


def n_floor(d: float = R3_EFFECT_D, alpha: float = ALPHA, power: float = POWER) -> int:
    """Per-group n needed to detect effect ``d`` with the stated power."""
    return math.ceil(2.0 * (_z_sum(alpha, power) / d) ** 2)


R3_N_FLOOR = n_floor(R3_EFFECT_D)
