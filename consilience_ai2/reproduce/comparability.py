"""F1 faithfulness: is the reproduction the same quantity, a proxy, or a substitution?

The asta-flows rubric: "Is the independent test the same quantity, a proxy, or a
substitution? A proxy is a caveat carried with the verdict, never a verdict. A
substitution is not a reproduction and is not run." The record DECLARES the relation
(``quantity_mapping.relation``); this module checks the declaration against what can be
checked, fail-closed, and adds ``not_comparable(<what>)`` when something differs that
must not:

- a number that cannot be read (``unparseable``);
- the quantity names: with no declared mapping they must be equal after
  ``core.normalise``; a declared ``same_quantity`` with different names is refused
  (declare ``proxy`` with a note instead);
- the effect-size type (``r`` vs ``d``) when either side gives one;
- the units: both stated, and of the same kind (convertible);
- every condition, except the declared ``independence_axis``, which must be stated on
  both sides and must DIFFER ("only independent data counts").

Units and conditions are compared by the optional ``consilience`` package
(``consilience.compare``: unit conversion through pint, typed condition comparison,
optional domain packs, named defects) when it is installed. Without it, a fallback
compares units by name (with ``%``/``percent`` and the dimensionless spellings as the
only conversions) and conditions by exact value after ``core.normalise`` for text. The
backend used is recorded in every F1 finding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from consilience_ai2.core.normalise import normalise
from consilience_ai2.reproduce.record import Parsed

BACKENDS = ("auto", "consilience", "fallback")
F1_ORDER = ("substitution", "not_comparable", "proxy", "same_quantity")


def consilience_version() -> str | None:
    """The installed ``consilience`` version, or None when it is absent or unusable."""
    try:
        import consilience  # noqa: PLC0415
    except ImportError:
        return None
    if not callable(getattr(consilience, "compare", None)):
        return None
    return str(getattr(consilience, "__version__", "unknown"))


def resolve_backend(backend: str = "auto") -> str:
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}")
    have = consilience_version() is not None
    if backend == "consilience" and not have:
        raise ValueError("backend 'consilience' requested but the consilience package is "
                         "not installed (pip install 'consilience-ai2[consilience]')")
    if backend == "auto":
        return "consilience" if have else "fallback"
    return backend


def backend_label(backend: str) -> str:
    return f"consilience {consilience_version()}" if backend == "consilience" else "fallback"


@dataclass
class Faithfulness:
    cls: str  # same_quantity | proxy | substitution | not_comparable
    mismatches: list[dict[str, str]] = field(default_factory=list)
    backend: str = "fallback"
    declared: str | None = None
    caveats: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.cls == "not_comparable":
            targets = sorted({m["target"] for m in self.mismatches})
            return f"not_comparable({', '.join(targets)})"
        return self.cls


# --------------------------------------------------------------------- fallback
_DIMENSIONLESS = {"", "1", "dimensionless", "unitless", "none", "-"}
_PERCENT = {"%", "percent", "pct"}


def _canon_unit(u: str) -> str:
    s = " ".join(u.split()).casefold()
    if s in _DIMENSIONLESS:
        return "dimensionless"
    if s in _PERCENT:
        return "percent"
    return s


def _fallback_factor(from_unit: str, to_unit: str) -> float | None:
    a, b = _canon_unit(from_unit), _canon_unit(to_unit)
    if a == b:
        return 1.0
    if {a, b} == {"percent", "dimensionless"}:
        return 0.01 if a == "percent" else 100.0
    return None


def _leaf(v: Any) -> tuple[str, Any]:
    if v is None:
        return ("unstated", None)
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, int | float):
        if not math.isfinite(float(v)):
            raise ValueError("non_finite")
        return ("number", float(v))
    if isinstance(v, str):
        s = normalise(v)
        if not s or s.casefold() == "unstated":
            return ("unstated", None)
        return ("text", s)
    if isinstance(v, dict):
        return ("record", v)
    if isinstance(v, list):
        return ("list", v)
    raise ValueError(f"unsupported condition type {type(v).__name__}")


def _fallback_conditions(ca: dict, cb: dict, path: str = "") -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for k in sorted(set(ca) | set(cb), key=str):
        p = f"{path}.{k}" if path else str(k)
        out.extend(_fallback_value(p, ca.get(k), cb.get(k), k in ca, k in cb))
    return out


def _fallback_value(p: str, va: Any, vb: Any, in_a: bool, in_b: bool) -> list[dict[str, str]]:
    if not (in_a and in_b):
        return [{"target": f"conditions.{p}", "reason": "not_stated",
                 "detail": f"stated on one side only (missing on "
                           f"{'source' if not in_a else 'reproduction'})"}]
    try:
        la, lb = _leaf(va), _leaf(vb)
    except ValueError as exc:
        return [{"target": f"conditions.{p}", "reason": "unparseable", "detail": str(exc)}]
    if la[0] == "unstated" or lb[0] == "unstated":
        return [{"target": f"conditions.{p}", "reason": "not_stated", "detail": "unstated"}]
    if la[0] != lb[0]:
        return [{"target": f"conditions.{p}", "reason": "different_kinds",
                 "detail": f"{la[0]} vs {lb[0]}"}]
    if la[0] == "record":
        return _fallback_conditions(la[1], lb[1], p)
    if la[0] == "list":
        if len(la[1]) != len(lb[1]):
            return [{"target": f"conditions.{p}", "reason": "differs",
                     "detail": "lists of different length"}]
        out: list[dict[str, str]] = []
        for i, (xa, xb) in enumerate(zip(la[1], lb[1], strict=True)):
            out.extend(_fallback_value(f"{p}[{i}]", xa, xb, True, True))
        return out
    if la[0] == "number":
        same = math.isclose(la[1], lb[1], rel_tol=1e-9, abs_tol=0.0)
    else:
        same = la[1] == lb[1]
    if same:
        return []
    return [{"target": f"conditions.{p}", "reason": "differs", "detail": f"{va!r} vs {vb!r}"}]


# ------------------------------------------------------------------ consilience
def _cons_defects(a_unit: str, b_unit: str, ca: dict, cb: dict,
                  pack: str | None) -> list[dict[str, str]]:
    import consilience  # noqa: PLC0415

    a = {"value": 0, "unit": a_unit, "conditions": ca}
    b = {"value": 0, "unit": b_unit, "conditions": cb}
    try:
        res = consilience.compare(a, b, pack=pack)
    except (consilience.InputError, consilience.RuleFileError) as exc:
        return [{"target": "conditions", "reason": "unparseable", "detail": str(exc)}]
    out = []
    for d in res.defects:
        t = d["target"]
        if t in ("a.value", "b.value"):
            continue
        if t == "unit":
            target = "unit"
        elif t in ("a.unit", "b.unit"):
            target = ("source" if t[0] == "a" else "reproduction") + ".unit"
        elif t.startswith(("a.conditions.", "b.conditions.")):
            target = "conditions." + t.split(".", 2)[2]
        else:
            target = f"conditions.{t}"
        reason = d["reason"] if d["verdict"] == "not_comparable" else \
            f"{d['verdict']}: {d['reason']}"
        out.append({"target": target, "reason": reason, "detail": d.get("detail") or ""})
    return out


def convert(x: float, from_unit: str, to_unit: str, backend: str) -> float:
    """``x`` in ``from_unit`` expressed in ``to_unit``. Raises ValueError."""
    if backend == "consilience":
        import consilience  # noqa: PLC0415

        res = consilience.compare({"value": 0, "unit": to_unit}, {"value": x, "unit": from_unit})
        if res.verdict not in ("agree", "within_floor", "disagree"):
            raise ValueError(f"cannot convert {from_unit!r} to {to_unit!r}: {res.label}")
        return float(res.b["value"])
    f = _fallback_factor(from_unit, to_unit)
    if f is None:
        raise ValueError(f"cannot convert {from_unit!r} to {to_unit!r} without consilience")
    return x * f


def convert_difference(x: float, from_unit: str, to_unit: str, backend: str) -> float:
    """A difference (width, standard error) converted between units (offsets cancel)."""
    return convert(x, from_unit, to_unit, backend) - convert(0.0, from_unit, to_unit, backend)


# ------------------------------------------------------------------------- F1
def check_faithfulness(rec: Parsed, backend: str = "auto", pack: str | None = None) -> Faithfulness:
    be = resolve_backend(backend)
    data = rec.data
    src, rep = rec.source, rec.reproduction
    mm: list[dict[str, str]] = []
    for u in rec.unreadable:
        if u.field.startswith(("source.", "reproduction.")):
            mm.append({"target": u.field, "reason": "unparseable", "detail": u.reason})

    mapping = data.get("quantity_mapping")
    declared = mapping["relation"] if mapping else None
    if src.quantity is None or rep.quantity is None:
        side = "source" if src.quantity is None else "reproduction"
        mm.append({"target": "quantity", "reason": "not_stated",
                   "detail": f"no quantity on the {side}"})
    else:
        same_name = normalise(src.quantity) == normalise(rep.quantity)
        if declared is None and not same_name:
            mm.append({"target": "quantity_mapping", "reason": "undeclared",
                       "detail": "the quantities differ and no mapping is declared"})
        elif declared == "same_quantity" and not same_name:
            mm.append({"target": "quantity", "reason": "differs",
                       "detail": "declared same_quantity, but the names differ; declare a "
                                 "proxy with a note, or use the same name"})

    se, re_ = src.effect, rep.effect
    if (se is None) != (re_ is None):
        mm.append({"target": "effect_size", "reason": "not_stated",
                   "detail": "an effect size on one side only"})
    elif se is not None and re_ is not None and se.type != re_.type:
        mm.append({"target": "effect_size.type", "reason": "differs",
                   "detail": f"{se.type} vs {re_.type}"})

    raw_a = data["source"].get("value")
    raw_b = data["reproduction"].get("value")
    unit_a, unit_b = src.unit, rep.unit
    if raw_a is not None or raw_b is not None:
        for side, u in (("source", unit_a), ("reproduction", unit_b)):
            if u is None or not u.strip():
                mm.append({"target": f"{side}.unit", "reason": "not_stated",
                           "detail": "write 'dimensionless' for a pure number"})
    units_given = bool(unit_a and unit_a.strip() and unit_b and unit_b.strip()) and (
        raw_a is not None or raw_b is not None)

    axis = data.get("independence_axis")
    ca, cb = dict(src.conditions), dict(rep.conditions)
    axis_a = ca.pop(axis, None) if axis else None
    axis_b = cb.pop(axis, None) if axis else None
    if axis:
        if axis_a is None or axis_b is None:
            mm.append({"target": f"conditions.{axis}", "reason": "not_stated",
                       "detail": "the independence axis must be stated on both sides"})
        else:
            if be == "consilience":
                diff = _cons_defects("dimensionless", "dimensionless",
                                     {axis: axis_a}, {axis: axis_b}, None)
            else:
                diff = _fallback_conditions({axis: axis_a}, {axis: axis_b})
            if not diff:
                mm.append({"target": f"conditions.{axis}", "reason": "not_independent",
                           "detail": "the reproduction must differ from the source on its "
                                     "independence axis"})

    pack = pack or data.get("conditions_pack")
    if be == "consilience":
        ua = unit_a if units_given else "dimensionless"
        ub = unit_b if units_given else "dimensionless"
        mm.extend(_cons_defects(ua, ub, ca, cb, pack))
    else:
        if pack:
            mm.append({"target": "conditions_pack", "reason": "unsupported",
                       "detail": "a conditions pack needs the consilience package"})
        if units_given and _fallback_factor(unit_a, unit_b) is None:  # type: ignore[arg-type]
            mm.append({"target": "unit", "reason": "not_convertible",
                       "detail": f"{unit_a!r} vs {unit_b!r} (fallback compares units by "
                                 "name; install consilience for conversion)"})
        mm.extend(_fallback_conditions(ca, cb))

    mm = sorted({(m["target"], m["reason"], m["detail"]): m for m in mm}.values(),
                key=lambda m: (m["target"], m["reason"], m["detail"]))
    caveats: list[str] = []
    if declared == "substitution":
        cls = "substitution"
    elif mm:
        cls = "not_comparable"
    elif declared == "proxy":
        cls = "proxy"
        note = mapping.get("note") if mapping else None
        caveats.append("proxy: " + (note or "the reproduction measures a proxy of the "
                                            "source quantity"))
    else:
        cls = "same_quantity"
    return Faithfulness(cls=cls, mismatches=mm, backend=backend_label(be),
                        declared=declared, caveats=caveats)
