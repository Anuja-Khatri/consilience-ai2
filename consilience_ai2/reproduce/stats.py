"""Closed-form power and test statistics for D1 and V1. No simulation, no randomness.

Effect-size types (``effect_size.type`` in a record) and the formulas used. ``n`` is the
reproduction's n; ``z_c`` and ``t_c`` are the standard-normal and Student-t critical
values at ``alpha`` (one-sided: ``1 - alpha``; two-sided: ``1 - alpha/2``); ``Phi`` is
the standard-normal CDF; ``T'(df, ncp)`` is the noncentral t distribution.

``r``   Pearson correlation. Fisher z approximation, ``z_r = atanh(|r|)``:
        power = ``Phi(z_r*sqrt(n-3) - z_c)`` (+ ``Phi(-z_r*sqrt(n-3) - z_c)`` two-sided).
        Needs n > 3. Test statistic ``t = r*sqrt(n-2)/sqrt(1-r^2)``, df = n - 2.
``d``   Cohen's d, two independent groups of sizes n1, n2 (``effect_size.n_groups``;
        default n1 = floor(n/2), n2 = n - n1). ``ncp = |d|*sqrt(n1*n2/(n1+n2))``,
        df = n1 + n2 - 2, power = ``P(T' > t_c)`` (+ ``P(T' < -t_c)`` two-sided).
        Test statistic ``t = d*sqrt(n1*n2/(n1+n2))``.
``dz``  Standardised mean of paired differences (one-sample t). ``ncp = |dz|*sqrt(n)``,
        df = n - 1; power as for ``d``. Test statistic ``t = dz*sqrt(n)``.
``h``   Cohen's h for two proportions, ``h = 2*asin(sqrt(p1)) - 2*asin(sqrt(p2))`` (a
        record may give ``type: proportions`` with ``p1`` and ``p2`` instead). Groups as
        for ``d``. power = ``Phi(|h|*sqrt(n1*n2/(n1+n2)) - z_c)`` (+ the other tail
        two-sided). Test statistic ``z = h*sqrt(n1*n2/(n1+n2))``.

Equivalence mode (a committed margin M instead of a minimum effect): the power of the
two one-sided tests when the reproduction equals the source exactly, with the
reproduction's standard error ``se`` (from ``se``, or from ``ci`` as in ``interval``):
power = ``max(0, 2*Phi(M/se - z(1-alpha)) - 1)``.

Power is always computed at the magnitude of the SOURCE effect with the REPRODUCTION's
n, for a test in the hypothesized direction (one-sided) or either direction
(two-sided): "it ran, but had too few cases to detect the source effect".

``p_from_effect`` gives the p-value of the committed test from an effect size and n,
used by V1 only when the record gives no p. One-sided p is in the hypothesized
direction.
"""

from __future__ import annotations

import math

from scipy import stats as _st

EFFECT_TYPES = ("r", "d", "dz", "h")


class PowerError(ValueError):
    """Power cannot be computed from what the record gives (a named reason)."""


def _groups(n: int, n_groups: tuple[int, int] | None) -> tuple[int, int]:
    if n_groups is not None:
        n1, n2 = n_groups
        if n1 + n2 != n:
            raise PowerError(f"n_groups {n1}+{n2} does not add up to n={n}")
        return n1, n2
    n1 = n // 2
    return n1, n - n1


def _crit_z(alpha: float, sides: int) -> float:
    return float(_st.norm.ppf(1 - alpha / sides))


def power(effect_type: str, effect: float, n: int, alpha: float, sides: int,
          n_groups: tuple[int, int] | None = None) -> float:
    """Power to detect ``|effect|`` with ``n`` cases. Raises ``PowerError``."""
    if effect_type not in EFFECT_TYPES:
        raise PowerError(f"no power formula for effect type {effect_type!r}")
    if sides not in (1, 2):
        raise PowerError("sides must be 1 or 2")
    e = abs(effect)
    if effect_type == "r":
        if n <= 3:
            raise PowerError("r needs n > 3")
        if e >= 1:
            raise PowerError("|r| must be below 1")
        zr = math.atanh(e) * math.sqrt(n - 3)
        zc = _crit_z(alpha, sides)
        p = _st.norm.cdf(zr - zc)
        if sides == 2:
            p += _st.norm.cdf(-zr - zc)
        return float(p)
    if effect_type == "h":
        n1, n2 = _groups(n, n_groups)
        if min(n1, n2) < 1:
            raise PowerError("h needs both groups non-empty")
        zh = e * math.sqrt(n1 * n2 / (n1 + n2))
        zc = _crit_z(alpha, sides)
        p = _st.norm.cdf(zh - zc)
        if sides == 2:
            p += _st.norm.cdf(-zh - zc)
        return float(p)
    if effect_type == "d":
        n1, n2 = _groups(n, n_groups)
        if min(n1, n2) < 2:
            raise PowerError("d needs at least 2 cases per group")
        df = n1 + n2 - 2
        ncp = e * math.sqrt(n1 * n2 / (n1 + n2))
    else:  # dz
        if n < 2:
            raise PowerError("dz needs n >= 2")
        df = n - 1
        ncp = e * math.sqrt(n)
    tc = float(_st.t.ppf(1 - alpha / sides, df))
    p = _st.nct.sf(tc, df, ncp)
    if sides == 2:
        p += _st.nct.cdf(-tc, df, ncp)
    return float(min(max(p, 0.0), 1.0))


def statistic(effect_type: str, effect: float, n: int,
              n_groups: tuple[int, int] | None = None) -> tuple[float, float | None]:
    """(statistic, df) for the test of ``effect`` = 0; df None means a z statistic."""
    if effect_type == "r":
        if n <= 2 or abs(effect) >= 1:
            raise PowerError("r test needs n > 2 and |r| < 1")
        return effect * math.sqrt((n - 2) / (1 - effect * effect)), float(n - 2)
    if effect_type == "d":
        n1, n2 = _groups(n, n_groups)
        if min(n1, n2) < 2:
            raise PowerError("d needs at least 2 cases per group")
        return effect * math.sqrt(n1 * n2 / (n1 + n2)), float(n1 + n2 - 2)
    if effect_type == "dz":
        if n < 2:
            raise PowerError("dz needs n >= 2")
        return effect * math.sqrt(n), float(n - 1)
    if effect_type == "h":
        n1, n2 = _groups(n, n_groups)
        if min(n1, n2) < 1:
            raise PowerError("h needs both groups non-empty")
        return effect * math.sqrt(n1 * n2 / (n1 + n2)), None
    raise PowerError(f"no test statistic for effect type {effect_type!r}")


def p_from_effect(effect_type: str, effect: float, n: int, sides: int, sign: int,
                  n_groups: tuple[int, int] | None = None) -> float:
    """p of the committed test. One-sided: in the direction ``sign`` (+1 or -1)."""
    stat, df = statistic(effect_type, effect, n, n_groups)
    dist = _st.norm if df is None else _st.t(df)
    if sides == 2:
        return float(min(1.0, 2 * dist.sf(abs(stat))))
    return float(dist.sf(sign * stat))


def z_crit(alpha: float, sides: int) -> float:
    return _crit_z(alpha, sides)


def equivalence_power(margin: float, se: float, alpha: float) -> float:
    """Power of the two one-sided tests at a true difference of zero."""
    if se <= 0:
        raise PowerError("the standard error must be positive")
    k = margin / se - float(_st.norm.ppf(1 - alpha))
    return float(max(0.0, 2 * _st.norm.cdf(k) - 1))


def se_from(ci: tuple[float, float] | None, ci_level: float | None,
            se: float | None) -> float | None:
    """A standard error: ``se`` itself, else ``(hi - lo) / (2*z((1+level)/2))``."""
    if se is not None:
        return se
    if ci is None:
        return None
    level = ci_level if ci_level is not None else 0.95
    return (ci[1] - ci[0]) / (2 * float(_st.norm.ppf((1 + level) / 2)))


def interval(value: float, *, ci: tuple[float, float] | None, ci_level: float | None,
             se: float | None, alpha: float) -> tuple[float, float] | None:
    """The (1 - 2*alpha) interval used by the equivalence test (two one-sided tests).

    From ``se`` when given: ``value -/+ z(1-alpha)*se``. Else from a reported ``ci`` at
    ``ci_level`` (default 0.95), converted to a standard error as
    ``(hi - lo) / (2*z((1+level)/2))`` and re-centred on ``value``. None when neither.
    """
    se = se_from(ci, ci_level, se)
    if se is None:
        return None
    half = float(_st.norm.ppf(1 - alpha)) * se
    return value - half, value + half
