"""Reproduction records: load, validate against the JSON Schema, and read the numbers.

A record is YAML or JSON (``reproduction_record.schema.json`` in ``data/``, version 1).
Loading has two stages, kept apart on purpose:

1. **Structure.** The file must parse, have no duplicate keys, and match the schema.
   A structural failure is a ``RecordError``; the checker reports it as ``S1`` and runs
   nothing else.
2. **Numbers.** Every number is read fail-closed. A YAML/JSON number must be finite and
   not a boolean. A string must hold exactly one number and nothing else, read with
   ``consilience_ai2.core.numbers`` (English separators; ``1.234,5`` or ``1,2`` are
   ambiguous and refused; a ``%`` is refused because the unit belongs in ``unit``). A
   number that cannot be read is not an exception: it is listed in
   ``Parsed.unreadable`` with its field and reason, and F1 reports it as
   ``not_comparable(<field>: unparseable)``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from consilience_ai2.core.hashing import sha256_file, sha256_json
from consilience_ai2.core.numbers import extract_numbers

SCHEMA_VERSION = 1
SCHEMA_ID = "consilience-ai2/reproduction-record/1"


class RecordError(ValueError):
    """The record cannot be read or does not match the schema."""


# ----------------------------------------------------------------------- loading
class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML with duplicate keys refused and timestamps kept as text (``2026-03-01``
    stays a string: a date is a condition value, not a number to convert)."""


_UniqueKeyLoader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in rs if tag != "tag:yaml.org,2002:timestamp"]
    for ch, rs in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise RecordError(f"duplicate key {key!r} (line {key_node.start_mark.line + 1})")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                                 _construct_mapping)


def _refuse_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise RecordError(f"duplicate key {k!r}")
        out[k] = v
    return out


def parse_text(text: str, name: str = "<record>") -> dict[str, Any]:
    """Parse YAML or JSON text into a dict (JSON when it starts with ``{``)."""
    try:
        if text.lstrip().startswith("{"):
            data = json.loads(text, object_pairs_hook=_refuse_dupes,
                              parse_constant=lambda c: c)
        else:
            data = yaml.load(text, Loader=_UniqueKeyLoader)  # noqa: S506 (safe loader)
    except RecordError:
        raise
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise RecordError(f"{name}: not valid YAML or JSON: {exc}") from None
    if not isinstance(data, dict):
        raise RecordError(f"{name}: a record is a mapping at the top level")
    return data


def load_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise RecordError(f"file not found: {path}")
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise RecordError(f"{path}: not UTF-8 text") from None
    return parse_text(text, str(path))


# ------------------------------------------------------------------------ schema
def schema() -> dict[str, Any]:
    """The record JSON Schema (the single source of truth for the structure)."""
    ref = resources.files("consilience_ai2.reproduce").joinpath(
        "data/reproduction_record.schema.json")
    return json.loads(ref.read_text(encoding="utf-8"))


_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, int | float) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def _validate(value: Any, sch: dict, root: dict, path: str, errors: list[str]) -> None:
    """A JSON Schema subset: $ref (local), type, const, enum, required, properties,
    additionalProperties (false), items, minItems, maxItems, minLength. Enough for the
    record schema; anything else in a schema is ignored, never guessed at."""
    if "$ref" in sch:
        ref = sch["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"only local $ref is supported: {ref}")
        target: Any = root
        for part in ref[2:].split("/"):
            target = target[part]
        _validate(value, target, root, path, errors)
        return
    where = path or "<record>"
    if "type" in sch:
        types = sch["type"] if isinstance(sch["type"], list) else [sch["type"]]
        if not any(_TYPES[t](value) for t in types):
            errors.append(f"{where}: expected {' or '.join(types)}, got {type(value).__name__}")
            return
    if "const" in sch and (value != sch["const"] or type(value) is not type(sch["const"])):
        errors.append(f"{where}: must be {sch['const']!r}")
    if "enum" in sch and not any(value == e and type(value) is type(e) for e in sch["enum"]):
        errors.append(f"{where}: must be one of {sch['enum']}, got {value!r}")
    if isinstance(value, str) and "minLength" in sch and len(value) < sch["minLength"]:
        errors.append(f"{where}: must not be empty")
    if isinstance(value, dict):
        for k in sch.get("required", []):
            if k not in value:
                errors.append(f"{where}: missing required field {k!r}")
        props = sch.get("properties", {})
        if sch.get("additionalProperties") is False:
            for k in sorted(set(value) - set(props), key=str):
                errors.append(f"{where}: unknown field {k!r}")
        for k, sub in props.items():
            if k in value:
                _validate(value[k], sub, root, f"{path}.{k}" if path else k, errors)
    if isinstance(value, list):
        if "minItems" in sch and len(value) < sch["minItems"]:
            errors.append(f"{where}: needs at least {sch['minItems']} items")
        if "maxItems" in sch and len(value) > sch["maxItems"]:
            errors.append(f"{where}: allows at most {sch['maxItems']} items")
        if "items" in sch:
            for i, item in enumerate(value):
                _validate(item, sch["items"], root, f"{where}[{i}]", errors)


def validate(data: Any) -> list[str]:
    """Schema errors for ``data`` (empty when it is a valid record), sorted."""
    sch = schema()
    errors: list[str] = []
    _validate(data, sch, sch, "", errors)
    th = data.get("thresholds") if isinstance(data, dict) else None
    if isinstance(th, dict):
        has_min = "minimum_effect" in th
        has_eq = "equivalence_margin" in th
        if has_min == has_eq:
            errors.append("thresholds: commit exactly one of minimum_effect or "
                          "equivalence_margin")
        if has_eq and "minimum_effect_scale" in th:
            errors.append("thresholds: minimum_effect_scale goes with minimum_effect")
    return sorted(errors)


# ----------------------------------------------------------------------- numbers
@dataclass(frozen=True)
class Unreadable:
    field: str
    reason: str


def read_number(v: Any) -> tuple[float | None, str | None]:
    """(value, None) or (None, reason). Fail closed: see the module docstring."""
    if v is None:
        return None, None
    if isinstance(v, bool):
        return None, "boolean_not_number"
    if isinstance(v, int | float):
        f = float(v)
        return (f, None) if math.isfinite(f) else (None, "non_finite")
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None, "empty"
        if s.casefold() in ("nan", "inf", "-inf", "+inf", "infinity", "-infinity"):
            return None, "non_finite"
        toks = extract_numbers(s)
        if len(toks) != 1:
            return None, "not_one_number" if toks else "no_number"
        t = toks[0]
        if not t.ok:
            return None, "ambiguous_separators"
        if t.percent:
            return None, "percent_sign: write the unit in 'unit'"
        if t.start != 0 or t.end != len(s):
            return None, "extra_text"
        return float(t.value), None  # type: ignore[arg-type]
    return None, f"not_a_number ({type(v).__name__})"


def read_count(v: Any) -> tuple[int | None, str | None]:
    x, why = read_number(v)
    if why or x is None:
        return None, why
    if x < 0 or x != int(x):
        return None, "not_a_count"
    return int(x), None


@dataclass
class Effect:
    type: str
    value: float | None
    n_groups: tuple[int, int] | None = None
    p1: float | None = None
    p2: float | None = None


@dataclass
class Measurement:
    quantity: str | None = None
    value: float | None = None
    unit: str | None = None
    n: int | None = None
    effect: Effect | None = None
    p: float | None = None
    ci: tuple[float, float] | None = None
    ci_level: float | None = None
    se: float | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    status: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def has_result(self) -> bool:
        """True when any result number is present (value, effect, p, interval)."""
        return any(x is not None for x in (self.value, self.p, self.ci, self.se)) or (
            self.effect is not None and self.effect.value is not None)


@dataclass
class Parsed:
    """A record whose numbers have been read. ``unreadable`` lists every number that
    could not be read, by field."""

    data: dict[str, Any]
    source: Measurement
    reproduction: Measurement
    alpha: float | None
    sides: int
    minimum_effect: float | None
    minimum_effect_scale: str
    equivalence_margin: float | None
    power_threshold: float | None
    positive_control_p: float | None
    unreadable: list[Unreadable]
    sha256: str
    path: str | None = None

    @property
    def mode(self) -> str:
        return "equivalence" if "equivalence_margin" in self.data["thresholds"] \
            else "minimum_effect"


def _cohens_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


def _measurement(d: dict[str, Any], side: str, bad: list[Unreadable]) -> Measurement:
    def num(key: str, v: Any) -> float | None:
        x, why = read_number(v)
        if why:
            bad.append(Unreadable(f"{side}.{key}", why))
        return x

    m = Measurement(quantity=d.get("quantity"), unit=d.get("unit"),
                    conditions=dict(d.get("conditions") or {}), status=d.get("status"),
                    raw=d)
    m.value = num("value", d.get("value"))
    n, why = read_count(d.get("n"))
    if why:
        bad.append(Unreadable(f"{side}.n", why))
    m.n = n
    p = num("p", d.get("p"))
    if p is not None and not 0 <= p <= 1:
        bad.append(Unreadable(f"{side}.p", "not_a_probability"))
        p = None
    m.p = p
    if "ci" in d:
        lo, hi = num("ci[0]", d["ci"][0]), num("ci[1]", d["ci"][1])
        if lo is not None and hi is not None:
            if lo > hi:
                bad.append(Unreadable(f"{side}.ci", "lower_above_upper"))
            else:
                m.ci = (lo, hi)
    lvl = num("ci_level", d.get("ci_level"))
    if lvl is not None and not 0 < lvl < 1:
        bad.append(Unreadable(f"{side}.ci_level", "not_a_probability"))
        lvl = None
    m.ci_level = lvl
    se = num("se", d.get("se"))
    if se is not None and se < 0:
        bad.append(Unreadable(f"{side}.se", "negative"))
        se = None
    m.se = se
    es = d.get("effect_size")
    if es is not None:
        etype = es["type"]
        ev = num("effect_size.value", es.get("value"))
        p1 = num("effect_size.p1", es.get("p1"))
        p2 = num("effect_size.p2", es.get("p2"))
        groups = None
        if "n_groups" in es:
            g = [read_count(x) for x in es["n_groups"]]
            if any(w for _, w in g):
                bad.append(Unreadable(f"{side}.effect_size.n_groups", "not_a_count"))
            else:
                groups = (g[0][0], g[1][0])  # type: ignore[assignment]
        if etype == "proportions":
            ok = p1 is not None and p2 is not None and 0 <= p1 <= 1 and 0 <= p2 <= 1
            if not ok:
                bad.append(Unreadable(f"{side}.effect_size", "proportions_need_p1_p2_in_[0,1]"))
            ev = _cohens_h(p1, p2) if ok else None  # type: ignore[arg-type]
            etype = "h"
        if etype == "r" and ev is not None and not -1 < ev < 1:
            bad.append(Unreadable(f"{side}.effect_size.value", "r_outside_(-1,1)"))
            ev = None
        m.effect = Effect(type=etype, value=ev, n_groups=groups, p1=p1, p2=p2)
    return m


def parse(data: dict[str, Any], *, path: str | Path | None = None,
          file_sha256: str | None = None) -> Parsed:
    """Validate ``data`` and read its numbers. Raises ``RecordError`` on schema errors."""
    errors = validate(data)
    if errors:
        raise RecordError("; ".join(errors))
    bad: list[Unreadable] = []
    src = _measurement(data["source"], "source", bad)
    rep = _measurement(data["reproduction"], "reproduction", bad)
    th = data["thresholds"]

    def num(key: str) -> float | None:
        x, why = read_number(th.get(key))
        if why:
            bad.append(Unreadable(f"thresholds.{key}", why))
        return x

    alpha = num("alpha")
    if alpha is not None and not 0 < alpha < 1:
        bad.append(Unreadable("thresholds.alpha", "not_in_(0,1)"))
        alpha = None
    power = num("power")
    if power is not None and not 0 < power < 1:
        bad.append(Unreadable("thresholds.power", "not_in_(0,1)"))
        power = None
    min_eff = num("minimum_effect")
    if min_eff is not None and min_eff < 0:
        bad.append(Unreadable("thresholds.minimum_effect", "negative"))
        min_eff = None
    margin = num("equivalence_margin")
    if margin is not None and margin < 0:
        bad.append(Unreadable("thresholds.equivalence_margin", "negative"))
        margin = None
    pc = data.get("positive_control") or {}
    pc_p, why = read_number(pc.get("p"))
    if why:
        bad.append(Unreadable("positive_control.p", why))
    return Parsed(
        data=data, source=src, reproduction=rep, alpha=alpha,
        sides=int(th.get("sides", 2)), minimum_effect=min_eff,
        minimum_effect_scale=th.get("minimum_effect_scale", "effect_size"),
        equivalence_margin=margin,
        power_threshold=power if "power" in th else 0.8,
        positive_control_p=pc_p,
        unreadable=sorted(bad, key=lambda u: (u.field, u.reason)),
        sha256=file_sha256 or sha256_json(data),
        path=str(path) if path is not None else None,
    )


def parse_file(path: str | Path) -> Parsed:
    return parse(load_file(path), path=path, file_sha256=sha256_file(path))
