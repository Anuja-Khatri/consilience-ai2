"""Number reading for W1, rules v0.2: ``core.numbers`` plus five additions.

``core.numbers.extract_numbers`` reads digits. W1 rules v0.2 (``W1_RULES_V2``) start
from its tokens and add, in this order:

1. **Bare powers.** ``10^2``, ``10**2``, ``10^{-3}``, ``2^10`` and ``10⁻³`` are one number
   (core reads ``10^2`` as 10 and 2, and skips ``10³``). ``10^k`` has the precision of its
   order of magnitude (value 10^k, quantum 10^k); any other base gives the exact power.
   A power after a mantissa and a multiplication sign (``1.5 × 10^-3``) is left to core,
   which already reads it whole. An exponent outside -30..30 is ambiguous (uncheckable).
2. **Percent words.** ``50 percent``, ``50 per cent``, ``50 pct`` and ``5 percentage
   points`` are percentages, like ``50%``, so they take part in the percent-fraction
   equivalence (``50 percent`` against ``0.5``).
3. **Scale words.** ``1.5 million`` is 1.5e6 at the precision of the last printed digit
   (quantum 1e5); likewise ``thousand``, ``billion`` and ``trillion``.
4. **Scale suffixes**, written directly after the digits and followed by no letter or
   digit. ``k`` and ``bn`` are read as thousand and billion. ``K``, ``M`` and ``B`` are
   also units (kelvin, molar, bytes), so they are read *both ways*: ``2M`` is two
   readings, 2 and 2e6, and a claim number is supported when any of its readings is.
5. **Number words.** Cardinals from ``zero`` to ``nineteen``, the tens ``twenty`` to
   ``ninety`` and the multipliers ``hundred``, ``thousand``, ``million``, ``billion``
   and ``trillion``, combined as written (``twenty-five``, ``two hundred and five``,
   ``a thousand``). A phrase ending in a multiplier has that multiplier's precision
   (``two hundred`` is 200 with quantum 100); otherwise it is an exact integer.
   Not read, by decision:

   - ``one`` alone, which is far more often a pronoun or determiner ("one of the",
     "no one") than a quantity; it is read inside a compound (``one hundred``,
     ``twenty-one``);
   - a number word joined by a hyphen to a following word that is not a number word
     (``two-stage``, ``zero-shot``, ``three-dimensional``): a compound modifier, not a
     stated quantity;
   - plurals (``hundreds``, ``millions``), which are vague;
   - ordinals (``first``, ``third``) and fractions written as words;
   - the relations ``half``, ``twice``, ``double``, ``triple``: they state a ratio
     between two quantities, which a source supports by giving the two quantities, not
     by printing the ratio, so reading them would flag correct claims.

Signs (used by ``claims._supported`` under v0.2): a number's sign is *explicit* when
its text starts with ``+``, ``-`` or ``−``. Two explicit signs that differ do not agree;
an unsigned number agrees with either sign (the sign is often carried by a word such
as "fell").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation

from consilience_ai2.core.numbers import SUPERSCRIPT, NumberToken, extract_numbers

W1_RULES_V1 = "consilience-ai2.w1/1"
W1_RULES_V2 = "consilience-ai2.w1/2"

MAX_POWER = 30

_POWER = re.compile(
    r"(?P<base>\d+(?:\.\d+)?)"
    r"(?:[ \t]*(?:\^|\*\*)[ \t]*(?:\{[ \t]*(?P<bexp>[+\-−]?\d+)[ \t]*\}|(?P<exp>[+\-−]?\d+))"
    r"|(?P<sup>[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+))")
_TIMES_BEFORE = re.compile(r"(?:(?<![A-Za-z])x|[×·*]|\\times|\\cdot)[ \t]*$")
_PCT_WORD = re.compile(r"[ \t]+(?:percent|per[ \t]+cent|pct|percentage[ \t]+points?)\b",
                       re.IGNORECASE)
_SCALE_WORD = re.compile(r"[ \t]+(thousand|million|billion|trillion)\b(?!-)", re.IGNORECASE)
_SUFFIX = re.compile(r"(bn|k|K|M|B)(?![A-Za-z0-9_])")
SCALE_EXP = {"thousand": 3, "million": 6, "billion": 9, "trillion": 12}
SUFFIX_EXP = {"k": 3, "bn": 9, "K": 3, "M": 6, "B": 9}
SUFFIX_BOTH_WAYS = frozenset({"K", "M", "B"})

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
         "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
         "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
        "eighty": 80, "ninety": 90}
MULTIPLIERS = {"hundred": 2, "thousand": 3, "million": 6, "billion": 9, "trillion": 12}
NUMBER_WORDS = frozenset(UNITS) | frozenset(TENS) | frozenset(MULTIPLIERS)
_WORD_TOKEN = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class W1Number:
    """One number as written, with one or more readings (``readings[0]`` is the main one)."""

    text: str
    start: int
    end: int
    readings: tuple[NumberToken, ...]

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.readings)

    @property
    def main(self) -> NumberToken:
        return self.readings[0]


def explicit_sign(tok: NumberToken) -> str | None:
    """``+`` or ``-`` when the token's text starts with a sign, else None."""
    if tok.text[:1] in ("-", "−"):
        return "-"
    if tok.text[:1] == "+":
        return "+"
    return None


def _decimal_places(v: Decimal) -> int:
    exp = v.normalize().as_tuple().exponent
    return max(0, -exp) if isinstance(exp, int) else 0


def _power_token(text: str, m: re.Match[str]) -> NumberToken:
    raw = m.group("exp") or m.group("bexp") or m.group("sup").translate(SUPERSCRIPT)
    raw = raw.replace("−", "-")
    base_s = m.group("base")
    span = dict(text=text[m.start():m.end()], start=m.start(), end=m.end())
    try:
        e = int(raw)
    except ValueError:
        return NumberToken(value=None, decimals=0, status="ambiguous", **span)
    if abs(e) > MAX_POWER:
        return NumberToken(value=None, decimals=0, status="ambiguous", **span)
    if base_s == "10":
        return NumberToken(value=Decimal(1).scaleb(e), decimals=0, exponent=e, **span)
    try:
        v = Decimal(base_s) ** e
    except (InvalidOperation, ArithmeticError):
        return NumberToken(value=None, decimals=0, status="ambiguous", **span)
    return NumberToken(value=v, decimals=_decimal_places(v), **span)


def _powers(text: str) -> list[NumberToken]:
    out: list[NumberToken] = []
    for m in _POWER.finditer(text):
        s = m.start()
        if s > 0 and (text[s - 1].isalnum() or text[s - 1] in "_.^"):
            continue  # glued to an identifier, or itself an exponent
        if _TIMES_BEFORE.search(text, 0, s):
            continue  # mantissa x 10^k: core reads it whole
        out.append(_power_token(text, m))
    return out


def _is_exponent_of_symbol(text: str, tok: NumberToken) -> bool:
    """True for the exponent in ``x^2`` or ``x**2``: a power of a symbol, not a quantity."""
    before = text[:tok.start].rstrip(" \t{")
    return before.endswith("^") or before.endswith("**")


def _scaled(tok: NumberToken, k: int, text: str, end: int) -> NumberToken:
    """``tok`` times 10^k, keeping its printed precision (quantum times 10^k)."""
    assert tok.value is not None
    return replace(tok, text=text[tok.start:end], end=end, value=tok.value.scaleb(k),
                   exponent=(tok.exponent or 0) + k, uncertainty=None)


def _category(w: str) -> str:
    if w in UNITS:
        return "unit"
    if w in TENS:
        return "tens"
    if w == "hundred":
        return "hundred"
    return "big"


def _may_follow(prev: str | None, prev_word: str | None, cat: str, word: str,
                biggest: int | None) -> bool:
    """Whether ``word`` (of category ``cat``) may continue a cardinal phrase."""
    if prev is None:
        return cat in ("unit", "tens")
    if prev == "unit":
        if cat == "hundred":
            return True
        return cat == "big" and (biggest is None or MULTIPLIERS[word] < biggest)
    if prev == "tens":
        if cat == "unit":
            return 1 <= UNITS[word] <= 9
        if cat == "hundred":
            return False
        return cat == "big" and (biggest is None or MULTIPLIERS[word] < biggest)
    if prev == "hundred":
        if cat in ("unit", "tens"):
            return True
        return cat == "big" and (biggest is None or MULTIPLIERS[word] < biggest)
    # prev == "big"
    return cat in ("unit", "tens")


def _word_numbers(text: str) -> list[NumberToken]:
    """Cardinal number phrases written as words (see the module docstring)."""
    toks = [(m.group(0).lower(), m.start(), m.end()) for m in _WORD_TOKEN.finditer(text)]
    out: list[NumberToken] = []
    i = 0
    while i < len(toks):
        w, s, e = toks[i]
        lead_a = (w == "a" and i + 1 < len(toks) and toks[i + 1][0] in MULTIPLIERS
                  and re.fullmatch(r"[ \t]+", text[e:toks[i + 1][1]]) is not None)
        if not (w in UNITS or w in TENS or lead_a) or (
                s > 0 and (text[s - 1].isalnum() or text[s - 1] in "_-‐")):
            i += 1
            continue
        j = i + 1 if lead_a else i
        prev: str | None = "unit" if lead_a else None
        prev_word: str | None = "one" if lead_a else None
        biggest: int | None = None
        end = toks[i][2]
        nums: list[str] = ["one"] if lead_a else []
        while j < len(toks):
            w2, s2, e2 = toks[j]
            gap = text[end:s2]
            if nums or lead_a:
                if w2 == "and" and prev in ("hundred", "big") and j + 1 < len(toks) and \
                        re.fullmatch(r"[ \t]+", gap):
                    w3, s3, _ = toks[j + 1]
                    if (w3 in UNITS or w3 in TENS) and re.fullmatch(r"[ \t]+", text[e2:s3]):
                        end = e2
                        j += 1
                        continue
                    break
                if not re.fullmatch(r"[ \t]+|-|\u2010", gap):
                    break
            if w2 not in NUMBER_WORDS:
                break
            cat = _category(w2)
            if not _may_follow(prev, prev_word, cat, w2, biggest):
                break
            nums.append(w2)
            if cat == "big":
                biggest = MULTIPLIERS[w2]
            prev, prev_word = cat, w2
            end = e2
            j += 1
        nxt = text[end:end + 2]
        joined_mod = len(nxt) == 2 and nxt[0] in "-‐" and nxt[1].isalpha()
        glued = end < len(text) and (text[end].isalnum() or text[end] == "_")
        if not nums or nums == ["one"] or joined_mod or glued:
            i = max(j, i + 1)
            continue
        total = current = 0
        last_mult: int | None = None
        for x in nums:
            if x in UNITS:
                current += UNITS[x]
                last_mult = None
            elif x in TENS:
                current += TENS[x]
                last_mult = None
            elif x == "hundred":
                current = (current or 1) * 100
                last_mult = 2
            else:
                total += (current or 1) * 10 ** MULTIPLIERS[x]
                current = 0
                last_mult = MULTIPLIERS[x]
        value = Decimal(total + current)
        phrase = text[s:end]
        if last_mult is not None:
            out.append(NumberToken(text=phrase, start=s, end=end, value=value, decimals=0,
                                   exponent=last_mult))
        else:
            out.append(NumberToken(text=phrase, start=s, end=end, value=value, decimals=0))
        i = j
    return out


def extract_w1_numbers(text: str) -> list[W1Number]:
    """Every number in ``text`` under W1 rules v0.2, in order of position."""
    core = extract_numbers(text)
    powers = _powers(text)
    # a power replaces the core tokens inside its span, unless one core token covers it
    kept_powers = [p for p in powers
                   if not any(c.start <= p.start and c.end >= p.end and (c.start, c.end) != (
                       p.start, p.end) for c in core)]
    covered = [(p.start, p.end) for p in kept_powers]
    base = [c for c in core if not any(a <= c.start and c.end <= b for a, b in covered)
            and not _is_exponent_of_symbol(text, c)]
    numbers: list[W1Number] = []
    for c in base:
        readings: list[NumberToken] = [c]
        if c.ok and c.value is not None and c.role == "value":
            pm = _PCT_WORD.match(text, c.end)
            sw = _SCALE_WORD.match(text, c.end)
            sx = _SUFFIX.match(text, c.end) if not c.percent else None
            if pm and not c.percent:
                readings = [replace(c, text=text[c.start:pm.end()], end=pm.end(), percent=True,
                                    uncertainty=None)]
            elif sw and not c.percent and c.exponent is None:
                readings = [_scaled(c, SCALE_EXP[sw.group(1).lower()], text, sw.end())]
            elif sx and c.exponent is None:
                k = SUFFIX_EXP[sx.group(1)]
                scaled = _scaled(c, k, text, sx.end())
                readings = [scaled, c] if sx.group(1) in SUFFIX_BOTH_WAYS else [scaled]
        r0 = readings[0]
        numbers.append(W1Number(r0.text, r0.start, r0.end, tuple(readings)))
    for p in kept_powers:
        numbers.append(W1Number(p.text, p.start, p.end, (p,)))
    taken = [(n.start, n.end) for n in numbers]
    for w in _word_numbers(text):
        if not any(a < w.end and w.start < b for a, b in taken):
            numbers.append(W1Number(w.text, w.start, w.end, (w,)))
    numbers.sort(key=lambda n: (n.start, n.end))
    return numbers


def source_readings(text: str) -> list[NumberToken]:
    """Every reading of every number in ``text`` (v0.2), for use as a W1 source."""
    return [r for n in extract_w1_numbers(text) for r in n.readings]
