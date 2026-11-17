"""Deterministic number extraction with printed precision and span offsets.

``extract_numbers(text)`` returns every number written in ``text`` as a ``NumberToken``:
the text as written, its exact ``Decimal`` value, the number of decimal places printed,
whether it is a percentage, its exponent if written in scientific notation, and its
``[start, end)`` offsets in ``text``. A number written as ``3.2 ± 0.4`` gives two tokens;
the first carries the second as its ``uncertainty``.

What counts as a number (the rules, in full)
- Digits with an optional decimal point (``12``, ``0.25``, ``.5``), an optional sign
  (``-``, ``+`` or U+2212 ``−``), an optional exponent and an optional ``%``.
- Exponents: ``1.5e-3`` / ``1.5E+03``; ``1.5 × 10^-3``, ``1.5 x 10^-3``, ``1.5*10**-3``,
  ``1.5 · 10^{-3}`` and LaTeX ``1.5 \\times 10^{-3}``; and superscripts ``1.5×10⁻³``.
- Percent: ``45%``, ``45 %`` and LaTeX ``45\\%``. The value stays 45; ``percent`` is True.
- ``±``, ``+/-`` and LaTeX ``\\pm`` link a value to its uncertainty.
- A sign belongs to the number only at the start of the text or after whitespace or one
  of ``( [ { = : ; , < > ≤ ≥ ~ ≈ /``. So ``10-20`` is 10 and 20, and ``p=-0.3`` is -0.3.

What is not a number (skipped, never guessed)
- Digits glued to a preceding letter, digit, underscore or dot: ``F1``, ``e595.3``,
  ``v0.1``, ``x2``.
- Digits after a hyphen that follows a letter: ``COVID-19``, ``Type-2`` (names).
- A token followed by an identifier-like run that contains more digits: ``3f9a``,
  ``21d2b9`` (hashes). Letters alone may follow (units: ``50ms``, ``3 kg``).
- Ordinals: ``1st``, ``2nd``, ``3rd``, ``4th``.
- ISO dates ``2026-11-17`` (as a whole).

Separators: fail closed
Commas and dots between digits are read with the English convention: ``,`` groups
thousands in groups of exactly three digits, ``.`` is the decimal point. Under it
``1,234`` is 1234 and ``1,234.5`` is 1234.5. Everything else that mixes separators is
**ambiguous** and is returned with ``status="ambiguous"`` and ``value=None``, never read:
``1.234,5`` (European), ``1,2`` and ``12,34`` (decimal comma or a list?), ``1.234.567``
and ``0.1.0`` (grouping dots or a version?). With ``convention="strict"`` any comma
between digits is ambiguous, including ``1,234``. Callers must treat an ambiguous token
as uncheckable, not as a mismatch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Decimal,
    DecimalException,
    InvalidOperation,
    localcontext,
)

SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")
SIGN_CHARS = "+-−"
SIGN_OK_BEFORE = set(" \t\r\n([{=:;,<>≤≥~≈/")
CONVENTIONS = ("en", "strict")

_EXP = (
    r"(?:"
    r"[eE](?P<e1>[+\-−]?\d+)"
    r"|[ \t]*(?:[x×·*]|\\times|\\cdot)[ \t]*10[ \t]*(?:\^|\*\*)[ \t]*\{?[ \t]*"
    r"(?P<e2>[+\-−]?\d+)[ \t]*\}?"
    r"|[ \t]*(?:[x×·]|\\times)[ \t]*10(?P<e3>[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)"
    r")"
)
_NUM = re.compile(
    r"(?P<sign>[+\-−])?"
    r"(?P<mant>\d[\d,.]*\d|\d|\.\d+)"
    r"(?P<exp>" + _EXP + r")?"
    r"(?P<pct>[ \t]?\\?%)?"
)
_PM = re.compile(r"[ \t]*(?:±|\+/-|\\pm)[ \t]*")
_ISO_DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_ORDINAL = ("st", "nd", "rd", "th")
_EN_GROUPED = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$")
_PLAIN = re.compile(r"^(?:\d+(?:\.\d*)?|\.\d+)$")


@dataclass(frozen=True)
class NumberToken:
    """One number as written. ``value`` is None when ``status == "ambiguous"``."""

    text: str
    start: int
    end: int
    value: Decimal | None
    decimals: int
    percent: bool = False
    exponent: int | None = None
    status: str = "ok"
    role: str = "value"  # "value" or "uncertainty" (the number after ±)
    uncertainty: NumberToken | None = field(default=None, compare=False)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def quantum(self) -> Decimal | None:
        """Half the printed resolution is ``quantum / 2``: 0.25 -> 0.01, 1.5e-3 -> 1e-4."""
        if self.value is None:
            return None
        return Decimal(1).scaleb(-self.decimals + (self.exponent or 0))

    def as_float(self) -> float | None:
        return None if self.value is None else float(self.value)

    def to_dict(self) -> dict:
        d = {
            "text": self.text, "start": self.start, "end": self.end,
            "value": None if self.value is None else str(self.value),
            "decimals": self.decimals, "percent": self.percent,
            "exponent": self.exponent, "status": self.status, "role": self.role,
        }
        if self.uncertainty is not None:
            d["uncertainty"] = self.uncertainty.to_dict()
        return d


def _read_mantissa(mant: str, convention: str) -> tuple[Decimal | None, int, str]:
    """(value, decimals, status) for the mantissa digits as written."""
    if "," in mant:
        if convention == "en" and _EN_GROUPED.match(mant):
            plain = mant.replace(",", "")
        else:
            return None, 0, "ambiguous"
    else:
        plain = mant
    if not _PLAIN.match(plain):
        return None, 0, "ambiguous"
    decimals = len(plain.split(".", 1)[1]) if "." in plain else 0
    try:
        return Decimal(plain), decimals, "ok"
    except InvalidOperation:  # pragma: no cover - guarded by _PLAIN
        return None, 0, "ambiguous"


def _is_identifier_tail(text: str, end: int) -> bool:
    """True when the run of [A-Za-z0-9_] starting at ``end`` makes this an identifier or
    an ordinal rather than a number followed by a unit."""
    j = end
    while j < len(text) and (text[j].isalnum() or text[j] == "_"):
        j += 1
    run = text[end:j]
    if not run:
        return False
    if any(c.isdigit() for c in run):
        return True
    return run.lower() in _ORDINAL


def _glued_before(text: str, pos: int) -> bool:
    """True when the character before ``pos`` glues these digits to an identifier."""
    if pos == 0:
        return False
    prev = text[pos - 1]
    if prev.isalnum() or prev in "_.":
        return True
    # COVID-19, Type-2: digits after a hyphen that follows a letter
    if prev in "-‐" and pos >= 2 and text[pos - 2].isalpha():
        return True
    return False


def _match_at(text: str, pos: int, convention: str, role: str) -> NumberToken | None:
    m = _NUM.match(text, pos)
    if not m:
        return None
    sign = m.group("sign")
    start = m.start()
    digits_start = m.start("mant")
    if sign:
        if start > 0 and text[start - 1] not in SIGN_OK_BEFORE:
            return None  # a hyphen inside a range or a word, not a sign
    elif _glued_before(text, digits_start):
        return None
    if m.group("mant").startswith(".") and start > 0 and text[start - 1].isdigit():
        return None
    end = m.end()
    if _is_identifier_tail(text, end):
        return None
    value, decimals, status = _read_mantissa(m.group("mant"), convention)
    exponent: int | None = None
    if m.group("exp"):
        raw = m.group("e1") or m.group("e2") or (m.group("e3") or "").translate(SUPERSCRIPT)
        exponent = int(raw.replace("−", "-"))
    if value is not None:
        if sign in ("-", "−"):
            value = -value
        if exponent is not None:
            value = value.scaleb(exponent)
    return NumberToken(
        text=text[start:end], start=start, end=end, value=value, decimals=decimals,
        percent=bool(m.group("pct")), exponent=exponent,
        status=status, role=role,
    )


def extract_numbers(text: str, convention: str = "en") -> list[NumberToken]:
    """Every number in ``text``, in order of position. See the module docstring."""
    if convention not in CONVENTIONS:
        raise ValueError(f"convention must be one of {CONVENTIONS}, got {convention!r}")
    dates = [(m.start(), m.end()) for m in _ISO_DATE.finditer(text)]
    tokens: list[NumberToken] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if not (c.isdigit() or c in SIGN_CHARS or c == "."):
            i += 1
            continue
        if any(s <= i < e for s, e in dates):
            i = next(e for s, e in dates if s <= i < e)
            continue
        tok = _match_at(text, i, convention, "value")
        if tok is None:
            # skip the whole digit run so its tail is not re-read as a new number
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in ",."):
                j += 1
            i = j if c.isdigit() else i + 1
            continue
        pm = _PM.match(text, tok.end)
        if pm:
            unc = _match_at(text, pm.end(), convention, "uncertainty")
            if unc is not None:
                tok = NumberToken(
                    text=tok.text, start=tok.start, end=tok.end, value=tok.value,
                    decimals=tok.decimals, percent=tok.percent, exponent=tok.exponent,
                    status=tok.status, role=tok.role, uncertainty=unc,
                )
                tokens.append(tok)
                tokens.append(unc)
                i = unc.end
                continue
        tokens.append(tok)
        i = tok.end
    return tokens


def agrees_at_printed_precision(printed: NumberToken, value: Decimal | float | int | str) -> bool:
    """True when ``value`` rounds to ``printed`` at the precision ``printed`` shows.

    ``printed`` = 0.24 (two places) agrees with 0.2381 and 0.2449 but not 0.2351.
    Rounding is accepted under either half-up or half-even, so a value exactly on a
    half-unit boundary agrees whichever convention printed it. Percent scaling is the
    caller's decision: compare 24.0% with 24.0, or with 0.240 after dividing by 100.
    An ambiguous token never agrees.

    It never raises on a number. A value more than one printed unit away from
    ``printed`` cannot round to it and is rejected before any rounding, so a huge value
    (``1e400`` against ``0.5``) is simply not agreeing. Rounding runs in a local decimal
    context wide enough for the printed digits, so a long printed integer (thirty
    digits) still compares exactly. Anything the decimal module still cannot represent
    counts as not agreeing (the caller treats it as unsupported), not as an exception.
    """
    if printed.value is None:
        return False
    try:
        v = Decimal(str(value)) if not isinstance(value, Decimal) else value
    except (InvalidOperation, ValueError, TypeError):
        return False
    target = printed.value
    if not v.is_finite() or not target.is_finite():
        return False
    q = printed.quantum
    assert q is not None
    try:
        with localcontext() as ctx:
            ctx.Emax, ctx.Emin = MAX_EMAX, MIN_EMIN
            # rounding to q moves a value by at most half a unit of q
            if abs(v - target) > q:
                return False
            # digits from the leading digit of the larger operand down to q, plus margin
            lead = max(v.adjusted(), target.adjusted(), q.adjusted())
            ctx.prec = max(ctx.prec, lead - q.adjusted() + 3)
            want = target.quantize(q)
            return any(v.quantize(q, rounding=r) == want
                       for r in (ROUND_HALF_UP, ROUND_HALF_EVEN))
    except DecimalException:
        return False
