"""D1 decidability, V1 verdict and P2 verbatim hypothesis. Pure functions of the record.

V1 never reads prose: ``notes``, ``note`` fields and ``reported_verdict`` are not
inputs to it (``reported_verdict`` is only compared with the result afterwards).

D1 decision table (first matching row wins)

| # | Condition | D1 |
|---|---|---|
| 1 | ``reproduction.status`` is ``no_data`` or ``not_run``, or the reproduction has no result numbers, or n = 0 | ``no_data`` |
| 2 | ``identifiability.identifiable`` is false | ``not_identifiable`` (with the record's reason) |
| 3 | power cannot be computed (no alpha, no source effect size, a zero source effect, no reproduction n, or a formula's own limit; in equivalence mode, no standard error or interval) | ``uncheckable`` (named reason) |
| 4 | power is below ``thresholds.power`` (default 0.8): at the source effect with the reproduction's n (minimum-effect mode), or of the two one-sided tests at zero difference with the reproduction's standard error (equivalence mode) | ``underpowered`` |
| 5 | otherwise | ``decidable`` |

Two verdict rules (``VERDICT_RULES``). ``v0.2`` (the default) judges the reproduction
against the SOURCE's finding: a reproduction tests the source's finding, not the
hypothesis wording. ``v0.1`` (the first release) judges it against the declared
``direction``. They differ only in minimum-effect mode; equivalence mode already tests
the source's value, sign included, and is the same in both.

V1 decision table, minimum-effect mode. ``s`` is the expected sign: under ``v0.2`` the
sign of the source effect on the committed scale, under ``v0.1`` the declared
``direction``, else the sign of the source effect. ``e`` is the reproduction effect on
the committed scale, ``m`` the committed minimum effect, ``sig`` is ``p < alpha`` (p from
the record, else computed from the effect and n, see ``stats.p_from_effect``). A one-sided
p in the record is in the declared ``direction`` (default: the source's sign); under
``v0.2``, when the expected sign is the other one, its complement ``1 - p`` is used,
except at a reproduction effect of exactly 0 (no evidence either way).

Under ``v0.2`` the source CLAIMS an effect when its effect on the committed scale is not
zero, at least ``m`` in size, and significant (its own p below alpha, in its own
direction). A source that claims no effect is ``undecided(source_null)``: a minimum-effect
record has no equivalence margin, and a null can only be reproduced by an equivalence
test (commit an ``equivalence_margin`` instead, which is judged by the two one-sided
tests below).

| # | Condition | Outcome | V1 |
|---|---|---|---|
| 1 | F1 is ``substitution`` | ``not_a_reproduction`` | ``inconclusive`` |
| 2 | F1 is ``not_comparable`` | ``undecided`` (not_comparable) | ``inconclusive`` |
| 3a | (v0.2) D1 is ``no_data`` or ``not_identifiable`` | ``undecided`` (the D1 class) | ``inconclusive`` |
| 3b | (v0.2) the source's effect or its test cannot be read | ``undecided`` (no_source_effect, no_source_test) | ``inconclusive`` |
| 3c | (v0.2) the source claims no effect | ``undecided`` (source_null) | ``inconclusive`` |
| 3 | D1 is not ``decidable`` | ``undecided`` (the D1 class) | ``inconclusive`` |
| 4 | a threshold, the effect, the direction or p cannot be read | ``undecided`` (named) | ``inconclusive`` |
| 5 | ``sig`` and ``s*e < 0`` | ``opposite_effect`` | ``not_reproduced`` |
| 6 | ``sig`` and ``s*e > 0`` and ``abs(e) >= m`` | ``supported`` | ``reproduced`` |
| 7 | ``s*e > 0`` and exactly one of ``sig``, ``abs(e) >= m`` | ``undecided`` (misses_threshold) | ``inconclusive`` |
| 8 | not ``sig``, and ``s*e <= 0`` or ``abs(e) < m``, and a positive control passed | ``rejected`` | ``not_reproduced`` |
| 9 | as 8, with no positive control | ``undecided`` (no_positive_control) | ``inconclusive`` |
| 10 | as 8, with a failed positive control | ``undecided`` (positive_control_failed) | ``inconclusive`` |
| 11 | ``sig`` and ``e = 0`` | ``undecided`` (inconsistent_numbers) | ``inconclusive`` |

Equivalence mode (``equivalence_margin`` M committed instead of a minimum effect): the
(1 - 2*alpha) interval of the reproduction value (in the source unit) against
``[S - M, S + M]`` around the source value S (two one-sided tests). Rows 1 to 4 as
above, then:

| # | Condition | Outcome | V1 |
|---|---|---|---|
| 5 | the interval lies inside ``[S - M, S + M]`` | ``supported`` | ``reproduced`` |
| 6 | the interval lies wholly outside it, beyond 0 on the side opposite to S | ``opposite_effect`` | ``not_reproduced`` |
| 7 | the interval lies wholly outside it otherwise | ``rejected`` (not_equivalent) | ``not_reproduced`` |
| 8 | otherwise (the interval overlaps a margin edge) | ``undecided`` (interval_overlaps_margin) | ``inconclusive`` |
| - | no interval (no ``se`` and no ``ci``) | ``undecided`` (no_interval) | ``inconclusive`` |

Positive control: ``positive_control.p < alpha`` when a p is given (the number wins over
a ``passed`` flag that disagrees, and the disagreement is reported), else
``positive_control.passed``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from consilience_ai2.core.normalise import NORMALISATION_VERSION, normalise
from consilience_ai2.reproduce import stats
from consilience_ai2.reproduce.comparability import Faithfulness, convert, convert_difference
from consilience_ai2.reproduce.record import Parsed

OUTCOMES = ("supported", "partly_supported", "opposite_effect", "rejected", "undecided",
            "not_a_reproduction")
VERDICT_OF = {
    "supported": "reproduced",
    "opposite_effect": "not_reproduced",
    "rejected": "not_reproduced",
    "partly_supported": "inconclusive",
    "undecided": "inconclusive",
    "not_a_reproduction": "inconclusive",
}
D1_CLASSES = ("decidable", "underpowered", "no_data", "not_identifiable", "uncheckable")
VERDICT_RULES = ("v0.1", "v0.2")
DEFAULT_RULE = "v0.2"


def _r(x: float | None, nd: int = 6) -> float | None:
    """Round a reported (not decided-on) number so the JSON is stable across platforms."""
    if x is None:
        return None
    return float(f"{x:.{nd}g}") if math.isfinite(x) else None


# --------------------------------------------------------------------------- D1
@dataclass
class Decidability:
    cls: str
    reason: str | None = None
    power: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


def check_decidability(rec: Parsed, backend: str = "fallback") -> Decidability:
    rep, src = rec.reproduction, rec.source
    if rep.status in ("no_data", "not_run"):
        why = "no independent data covered it" if rep.status == "no_data" else \
            "the test did not run"
        return Decidability("no_data", why)
    if not rep.has_result():
        return Decidability("no_data", "the reproduction gives no result numbers")
    if rep.n == 0:
        return Decidability("no_data", "the reproduction has n = 0")
    ident = rec.data.get("identifiability")
    if ident is not None and ident["identifiable"] is False:
        return Decidability("not_identifiable",
                            ident.get("reason") or "declared not identifiable")
    if rec.alpha is None:
        return Decidability("uncheckable", "no readable alpha")
    if rec.power_threshold is None:
        return Decidability("uncheckable", "no readable power threshold")
    if rec.mode == "equivalence":
        return _equivalence_decidability(rec, backend)
    if src.effect is None or src.effect.value is None:
        return Decidability("uncheckable", "no source effect size, so no power at it")
    if src.effect.value == 0:
        return Decidability("uncheckable", "the source effect is zero; power at it is "
                                           "undefined")
    if rep.n is None:
        return Decidability("uncheckable", "no reproduction n")
    groups = rep.effect.n_groups if rep.effect is not None else None
    try:
        pw = stats.power(src.effect.type, src.effect.value, rep.n, rec.alpha, rec.sides,
                         groups)
    except stats.PowerError as exc:
        return Decidability("uncheckable", str(exc))
    det = {"power": _r(pw), "power_threshold": rec.power_threshold,
           "at_source_effect": _r(src.effect.value), "effect_type": src.effect.type,
           "n": rep.n, "alpha": rec.alpha, "sides": rec.sides}
    if pw < rec.power_threshold:
        return Decidability("underpowered",
                            f"power {pw:.3f} at the source effect with n = {rep.n} is "
                            f"below {rec.power_threshold}", pw, det)
    return Decidability("decidable", None, pw, det)


def _equivalence_decidability(rec: Parsed, backend: str) -> Decidability:
    rep, src = rec.reproduction, rec.source
    margin = rec.equivalence_margin
    if margin is None:
        return Decidability("uncheckable", "no readable equivalence margin")
    se = stats.se_from(rep.ci, rep.ci_level, rep.se)
    if se is None:
        return Decidability("uncheckable", "no reproduction se or ci, so no power for the "
                                           "equivalence test")
    if rep.unit is None or src.unit is None:
        return Decidability("uncheckable", "units not stated")
    try:
        se = convert_difference(se, rep.unit, src.unit, backend)
        pw = stats.equivalence_power(margin, se, rec.alpha)  # type: ignore[arg-type]
    except (ValueError, stats.PowerError) as exc:
        return Decidability("uncheckable", str(exc))
    det = {"power": _r(pw), "power_threshold": rec.power_threshold, "mode": "equivalence",
           "margin": margin, "se": _r(se), "unit": src.unit, "alpha": rec.alpha}
    if pw < rec.power_threshold:
        return Decidability("underpowered",
                            f"power {pw:.3f} of the equivalence test at zero difference is "
                            f"below {rec.power_threshold}", pw, det)
    return Decidability("decidable", None, pw, det)


# --------------------------------------------------------------------------- V1
@dataclass
class Verdict:
    outcome: str
    verdict: str
    reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.outcome}({self.reason})" if self.outcome == "undecided" and \
            self.reason else self.outcome


def _undecided(reason: str, **details: Any) -> Verdict:
    return Verdict("undecided", "inconclusive", reason, dict(details))


def _positive_control(rec: Parsed) -> tuple[bool | None, dict[str, Any]]:
    pc = rec.data.get("positive_control")
    if not pc:
        return None, {}
    flag = pc.get("passed")
    if rec.positive_control_p is not None and rec.alpha is not None:
        by_num = rec.positive_control_p < rec.alpha
        det = {"positive_control_p": rec.positive_control_p, "passed": by_num}
        if flag is not None and flag != by_num:
            det["passed_flag_disagrees_with_p"] = True
        return by_num, det
    if flag is None:
        return None, {"positive_control": "given without p or passed"}
    return bool(flag), {"passed": bool(flag)}


def _direction(rec: Parsed) -> int:
    d = rec.data.get("direction")
    if d == "positive":
        return 1
    if d == "negative":
        return -1
    src = rec.source
    base = src.effect.value if src.effect is not None and src.effect.value is not None \
        else src.value
    if base is None or base == 0:
        return 0
    return 1 if base > 0 else -1


def _declared_sign(rec: Parsed) -> int:
    d = rec.data.get("direction")
    return 1 if d == "positive" else -1 if d == "negative" else 0


def _sign(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


def source_claim(rec: Parsed, backend: str = "fallback") -> tuple[bool | None, int,
                                                                   dict[str, Any], str | None]:
    """Does the source claim an effect, and in which direction? ``(claims, sign,
    details, reason)``; ``claims`` is None (with a ``reason``) when it cannot be read.

    The source effect is read on the committed scale (its value in the source unit, or
    its effect size). It claims an effect when that effect is not zero, at least the
    committed minimum effect in size, and significant in its own direction: the record's
    p (a one-sided p is in the declared ``direction``, so its complement ``1 - p`` is
    used when the source's sign is the other one), else p computed from the source's
    effect size and n."""
    src = rec.source
    m, alpha = rec.minimum_effect, rec.alpha
    if m is None or alpha is None:
        return None, 0, {}, "no_committed_threshold"
    if rec.minimum_effect_scale == "value":
        e = src.value
    else:
        e = src.effect.value if src.effect is not None else None
    if e is None:
        return None, 0, {}, "no_source_effect"
    s = _sign(e)
    p = src.p
    p_from = "record"
    if p is not None:
        declared = _declared_sign(rec)
        if rec.sides == 1 and declared != 0 and s != 0 and declared != s:
            p, p_from = 1 - p, "record, one-sided complement (1 - p)"
    elif src.effect is not None and src.effect.value is not None and src.n:
        try:
            p = stats.p_from_effect(src.effect.type, src.effect.value, src.n, rec.sides,
                                    _sign(src.effect.value) or 1, src.effect.n_groups)
        except stats.PowerError:
            return None, s, {}, "no_source_test"
        p_from = "computed from effect size and n"
    else:
        return None, s, {}, "no_source_test"
    sig = p < alpha
    big = abs(e) >= m
    claims = s != 0 and sig and big
    det = {"source_effect": _r(e), "source_p": _r(p), "source_p_from": p_from,
           "source_significant": sig, "source_meets_minimum_effect": big,
           "source_claims_effect": claims,
           "expected_direction": {1: "positive", -1: "negative", 0: None}[s]}
    declared = rec.data.get("direction")
    if declared is not None and s != 0 and _declared_sign(rec) != s:
        det["declared_direction"] = declared
        det["declared_direction_disagrees_with_source"] = True
    return claims, s, det, None


def check_verdict(rec: Parsed, f1: Faithfulness, d1: Decidability, backend: str,
                  rule: str = DEFAULT_RULE) -> Verdict:
    if rule not in VERDICT_RULES:
        raise ValueError(f"unknown verdict rule {rule!r} (one of {VERDICT_RULES})")
    if f1.cls == "substitution":
        return Verdict("not_a_reproduction", "inconclusive", "substitution",
                       {"note": "a substitution is not a reproduction and is not run"})
    if f1.cls == "not_comparable":
        return _undecided("not_comparable")
    claim: tuple[bool | None, int, dict[str, Any], str | None] | None = None
    unreadable_th = any(u.field.startswith("thresholds.") for u in rec.unreadable)
    if rule == "v0.2" and rec.mode == "minimum_effect":
        if d1.cls in ("no_data", "not_identifiable"):
            return _undecided(d1.cls)
        if not unreadable_th and rec.alpha is not None and rec.minimum_effect is not None:
            claim = source_claim(rec, backend)
            claims, _, cdet, why = claim
            if claims is None:
                return _undecided(why or "no_source_test", rule=rule)
            if not claims:
                return _undecided("source_null", rule=rule, **cdet)
    if d1.cls != "decidable":
        return _undecided(d1.cls)
    for u in rec.unreadable:
        if u.field.startswith(("thresholds.", "positive_control.")):
            return _undecided(f"unreadable {u.field}")
    alpha = rec.alpha
    assert alpha is not None  # D1 would be uncheckable otherwise
    if rec.mode == "equivalence":
        return _equivalence(rec, alpha, backend)
    return _minimum_effect(rec, alpha, backend, rule, claim)


def _minimum_effect(rec: Parsed, alpha: float, backend: str, rule: str = DEFAULT_RULE,
                    claim: tuple | None = None) -> Verdict:
    rep, src = rec.reproduction, rec.source
    m = rec.minimum_effect
    if m is None:
        return _undecided("no_committed_threshold")
    if rule == "v0.2":
        if claim is None:
            claim = source_claim(rec, backend)
        s, cdet = claim[1], claim[2]
    else:
        s, cdet = _direction(rec), {}
    if s == 0:
        return _undecided("no_direction")
    if rec.minimum_effect_scale == "value":
        if rep.value is None or src.unit is None or rep.unit is None:
            return _undecided("no_reproduction_value")
        try:
            e = convert(rep.value, rep.unit, src.unit, backend)
        except ValueError as exc:
            return _undecided(f"unit: {exc}")
    else:
        if rep.effect is None or rep.effect.value is None:
            return _undecided("no_reproduction_effect")
        e = rep.effect.value
    p = rep.p
    p_from = "record"
    if p is not None and rule == "v0.2" and rec.sides == 1 and e != 0:
        # at a zero effect there is no evidence in either direction (ties make a
        # one-sided p near 1 both ways), so the complement is not taken
        declared = _declared_sign(rec)
        if declared != 0 and declared != s:
            p, p_from = 1 - p, "record, one-sided complement (1 - p)"
    if p is None:
        if rep.effect is None or rep.effect.value is None or rep.n is None:
            return _undecided("no_test", note="no p, and no effect size with n to compute it")
        try:
            p = stats.p_from_effect(rep.effect.type, rep.effect.value, rep.n, rec.sides, s,
                                    rep.effect.n_groups)
        except stats.PowerError as exc:
            return _undecided("no_test", note=str(exc))
        p_from = "computed from effect size and n"
    sig = p < alpha
    big = abs(e) >= m
    se = s * e
    det: dict[str, Any] = {"mode": "minimum_effect", "effect": _r(e), "scale":
                           rec.minimum_effect_scale, "minimum_effect": m, "p": _r(p),
                           "p_from": p_from, "alpha": alpha, "sides": rec.sides,
                           "direction": "positive" if s > 0 else "negative",
                           "significant": sig, "meets_minimum_effect": big, "rule": rule,
                           **cdet}
    if sig and se < 0:
        return Verdict("opposite_effect", "not_reproduced", None, det)
    if sig and se > 0:
        if big:
            return Verdict("supported", "reproduced", None, det)
        return Verdict("undecided", "inconclusive", "misses_threshold", det)
    if sig:  # e == 0 yet significant
        return Verdict("undecided", "inconclusive", "inconsistent_numbers", det)
    if se > 0 and big:
        return Verdict("undecided", "inconclusive", "misses_threshold", det)
    passed, pcd = _positive_control(rec)
    det.update(pcd)
    if passed is True:
        return Verdict("rejected", "not_reproduced", None, det)
    reason = "no_positive_control" if passed is None else "positive_control_failed"
    return Verdict("undecided", "inconclusive", reason, det)


def _equivalence(rec: Parsed, alpha: float, backend: str) -> Verdict:
    rep, src = rec.reproduction, rec.source
    margin = rec.equivalence_margin
    if margin is None:
        return _undecided("no_committed_threshold")
    if src.value is None or rep.value is None or src.unit is None or rep.unit is None:
        return _undecided("no_value", note="equivalence needs both values and units")
    try:
        r = convert(rep.value, rep.unit, src.unit, backend)
        se = convert_difference(rep.se, rep.unit, src.unit, backend) if rep.se is not None \
            else None
        ci = None
        if rep.ci is not None:
            ci = (convert(rep.ci[0], rep.unit, src.unit, backend),
                  convert(rep.ci[1], rep.unit, src.unit, backend))
    except ValueError as exc:
        return _undecided(f"unit: {exc}")
    iv = stats.interval(r, ci=ci, ci_level=rep.ci_level, se=se, alpha=alpha)
    if iv is None:
        return _undecided("no_interval", note="give se or ci for the reproduction value")
    lo, hi = iv
    s_val = src.value
    band = (s_val - margin, s_val + margin)
    det = {"mode": "equivalence", "source_value": _r(s_val), "reproduction_value": _r(r),
           "interval": [_r(lo), _r(hi)], "interval_level": _r(1 - 2 * alpha),
           "band": [_r(band[0]), _r(band[1])], "margin": margin, "unit": src.unit}
    if band[0] <= lo and hi <= band[1]:
        return Verdict("supported", "reproduced", None, det)
    if hi < band[0] or lo > band[1]:
        opposite = (s_val > 0 and hi < 0) or (s_val < 0 and lo > 0)
        if opposite:
            return Verdict("opposite_effect", "not_reproduced", None, det)
        return Verdict("rejected", "not_reproduced", "not_equivalent", det)
    return Verdict("undecided", "inconclusive", "interval_overlaps_margin", det)


def aggregate(outcomes: list[str]) -> str:
    """The rubric outcome of a hypothesis committed as several components, one record
    each: ``supported`` when all are; ``opposite_effect`` when any is; ``rejected`` when
    all are; ``partly_supported`` ("one committed component met it") when at least one
    is supported and the rest are not; otherwise ``undecided``."""
    if not outcomes:
        return "undecided"
    for o in outcomes:
        if o not in OUTCOMES:
            raise ValueError(f"unknown outcome {o!r}")
    if any(o == "opposite_effect" for o in outcomes):
        return "opposite_effect"
    if all(o == "supported" for o in outcomes):
        return "supported"
    if all(o == "rejected" for o in outcomes):
        return "rejected"
    if any(o == "supported" for o in outcomes):
        return "partly_supported"
    return "undecided"


# --------------------------------------------------------------------------- P2
@dataclass
class HypothesisCopy:
    cls: str  # verbatim | reworded | uncheckable
    first_difference: int | None = None


def check_hypothesis(rec: Parsed) -> HypothesisCopy:
    h, s = rec.data.get("hypothesis"), rec.data.get("source_hypothesis")
    if not isinstance(h, str) or not isinstance(s, str) or not h.strip() or not s.strip():
        return HypothesisCopy("uncheckable")
    a, b = normalise(h), normalise(s)
    if a == b:
        return HypothesisCopy("verbatim")
    i = next((k for k, (x, y) in enumerate(zip(a, b, strict=False)) if x != y),
             min(len(a), len(b)))
    return HypothesisCopy("reworded", i)


__all__ = ["Decidability", "Verdict", "HypothesisCopy", "check_decidability",
           "check_verdict", "check_hypothesis", "aggregate", "source_claim", "OUTCOMES",
           "VERDICT_OF", "D1_CLASSES", "VERDICT_RULES", "DEFAULT_RULE",
           "NORMALISATION_VERSION"]
