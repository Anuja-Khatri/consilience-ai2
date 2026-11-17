"""W1 (number overreach) and W2 (certainty upgrade): claim-versus-source comparisons.

Both checks compare a *claim* (the text a reader sees: an ``.ev`` span, a Theorizer law,
a sentence citing a passage) with its *source* (the quote, the evidence record, the
cited passage). Both are lexical and deterministic; neither judges meaning.

W1, number overreach (``number_overreach``)
    Every number in the claim is read with ``core.numbers.extract_numbers``. A claim
    number is *supported* when some number in the source agrees with it at the claim's
    printed precision (``agrees_at_printed_precision``), comparing absolute values (the
    sign is often carried by a word such as "fell"), and allowing one percent scaling:
    a claim percentage ``45%`` agrees with a source fraction ``0.45`` and a claim
    fraction with a source percentage. Not checked, and listed as such:

    - ambiguous tokens (``1,2``; ``1.234,5``): uncheckable, never a mismatch;
    - year-like integers (an integer from 1900 to 2100 with no decimals, exponent or
      percent sign), which name dates or publication years far more often than
      quantities.

    A claim number with no supporting source number is flagged. Numbers written as words
    ("three") are not read.

W2, certainty upgrade (``certainty_upgrade``)
    Word lists in ``data/certainty_words.json`` (versioned). The claim is *assertive*
    when it contains an assertive word that is not negated and no hedged word; the
    source is *hedged* when it contains a hedged word and no non-negated assertive word.
    W2 flags an assertive claim over a hedged source. Matching is whole-word and
    case-insensitive on normalised text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from importlib import resources
from typing import Any

from consilience_ai2.core.normalise import normalise
from consilience_ai2.core.numbers import NumberToken, agrees_at_printed_precision, extract_numbers

YEAR_LO = 1900
YEAR_HI = 2100
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)*")


# --------------------------------------------------------------------------- W1


def is_year_like(tok: NumberToken) -> bool:
    """An integer from 1900 to 2100 written with no decimals, exponent or percent."""
    return (tok.ok and tok.decimals == 0 and tok.exponent is None and not tok.percent
            and tok.value is not None and YEAR_LO <= tok.value <= YEAR_HI)


def _candidates(src: NumberToken, claim: NumberToken) -> list[Decimal]:
    assert src.value is not None
    v = abs(src.value)
    out = [v]
    if claim.percent and not src.percent:
        out.append(v * 100)
    if src.percent and not claim.percent:
        out.append(v / 100)
    return out


def _agrees(target: NumberToken, v: Decimal) -> bool:
    """``agrees_at_printed_precision`` with two guards: a value further than one printed
    unit away cannot agree (this also skips values too large to quantize), and a
    ``decimal.InvalidOperation`` counts as no agreement."""
    q = target.quantum
    assert q is not None and target.value is not None
    try:
        if abs(v - target.value) > q:
            return False
        return agrees_at_printed_precision(target, v)
    except InvalidOperation:
        return False


def _supported(claim: NumberToken, source_tokens: list[NumberToken]) -> bool:
    assert claim.value is not None
    target = NumberToken(text=claim.text, start=claim.start, end=claim.end,
                         value=abs(claim.value), decimals=claim.decimals,
                         percent=claim.percent, exponent=claim.exponent)
    for s in source_tokens:
        if not s.ok:
            continue
        for v in _candidates(s, claim):
            if _agrees(target, v):
                return True
    return False


@dataclass(frozen=True)
class NumberCheck:
    """The W1 result for one claim against one source text."""

    unsupported: tuple[NumberToken, ...] = ()
    supported: tuple[NumberToken, ...] = ()
    ambiguous: tuple[NumberToken, ...] = ()
    years_skipped: tuple[NumberToken, ...] = ()

    @property
    def flagged(self) -> bool:
        return bool(self.unsupported)

    @property
    def checked(self) -> int:
        return len(self.unsupported) + len(self.supported)

    def details(self) -> dict[str, Any]:
        return {
            "unsupported": [t.text for t in self.unsupported],
            "unsupported_offsets": [[t.start, t.end] for t in self.unsupported],
            "supported": [t.text for t in self.supported],
            "ambiguous": [t.text for t in self.ambiguous],
            "years_skipped": [t.text for t in self.years_skipped],
        }


def number_overreach(claim: str, source: str,
                     source_tokens: list[NumberToken] | None = None) -> NumberCheck:
    """W1: the numbers in ``claim`` that no number in ``source`` supports.

    ``source_tokens`` may be passed when the same source is checked many times.
    """
    toks = source_tokens if source_tokens is not None else extract_numbers(source)
    uns: list[NumberToken] = []
    sup: list[NumberToken] = []
    amb: list[NumberToken] = []
    yrs: list[NumberToken] = []
    for c in extract_numbers(claim):
        if not c.ok:
            amb.append(c)
        elif is_year_like(c):
            yrs.append(c)
        elif _supported(c, toks):
            sup.append(c)
        else:
            uns.append(c)
    return NumberCheck(tuple(uns), tuple(sup), tuple(amb), tuple(yrs))


# --------------------------------------------------------------------------- W2


@dataclass(frozen=True)
class CertaintyWords:
    version: str
    hedged: frozenset[str]
    assertive: frozenset[str]
    negators: frozenset[str]
    negation_window: int


@lru_cache(maxsize=1)
def certainty_words() -> CertaintyWords:
    """The packaged, versioned W2 word lists."""
    raw = json.loads(resources.files("consilience_ai2.receipts").joinpath(
        "data/certainty_words.json").read_text(encoding="utf-8"))
    return CertaintyWords(
        version=raw["version"],
        hedged=frozenset(raw["hedged"]),
        assertive=frozenset(raw["assertive"]),
        negators=frozenset(raw["negators"]),
        negation_window=int(raw["negation_window"]),
    )


def words(text: str) -> list[str]:
    """Lower-cased word tokens of the normalised text (letters and inner apostrophes)."""
    return _WORD.findall(normalise(text).lower())


@dataclass(frozen=True)
class CertaintyProfile:
    hedged: tuple[str, ...] = ()
    assertive: tuple[str, ...] = ()
    negated_assertive: tuple[str, ...] = ()

    @property
    def is_assertive(self) -> bool:
        return bool(self.assertive) and not self.hedged

    @property
    def is_hedged(self) -> bool:
        return bool(self.hedged) and not self.assertive


def certainty_profile(text: str, lists: CertaintyWords | None = None) -> CertaintyProfile:
    """The hedged and (non-negated) assertive words in ``text``, in order of appearance."""
    cw = lists or certainty_words()
    toks = words(text)
    hedged: list[str] = []
    assertive: list[str] = []
    negated: list[str] = []
    for i, w in enumerate(toks):
        if w in cw.hedged:
            hedged.append(w)
        elif w in cw.assertive:
            window = toks[max(0, i - cw.negation_window):i]
            if any(p in cw.negators or p.endswith("n't") for p in window):
                negated.append(w)
            else:
                assertive.append(w)
    return CertaintyProfile(tuple(hedged), tuple(assertive), tuple(negated))


@dataclass(frozen=True)
class CertaintyCheck:
    claim: CertaintyProfile = field(default_factory=CertaintyProfile)
    source: CertaintyProfile = field(default_factory=CertaintyProfile)

    @property
    def flagged(self) -> bool:
        return self.claim.is_assertive and self.source.is_hedged

    def details(self) -> dict[str, Any]:
        return {
            "claim_assertive": list(self.claim.assertive),
            "claim_hedged": list(self.claim.hedged),
            "source_hedged": list(self.source.hedged),
            "source_assertive": list(self.source.assertive),
            "word_list": certainty_words().version,
        }


def certainty_upgrade(claim: str, source: str,
                      source_profile: CertaintyProfile | None = None) -> CertaintyCheck:
    """W2: an assertive claim over a hedged source."""
    sp = source_profile if source_profile is not None else certainty_profile(source)
    return CertaintyCheck(certainty_profile(claim), sp)
