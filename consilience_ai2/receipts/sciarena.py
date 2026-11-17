"""Adapter for SciArena-Eval: responses with inline citations and their cited passages.

Input: the released ``train.json`` (a list of votes). Each vote has ``responseA`` and
``responseB`` (text), ``citations_a`` and ``citations_b`` (each a list of
``{"concise_authors", "content", "title", "authors", "id"}``) and ``vote`` (``A`` or
``B``; any other value is a tie or missing and is excluded from paired comparisons).

Inline citations. A response cites a passage by writing its ``concise_authors`` string,
which in the released data always has the form ``<Name> et al. <year><letter>`` (for
example ``Dobek et al. 2022a``). Every match of ``INLINE`` in a response is one inline
citation. It *resolves* when its text equals the ``concise_authors`` of a citation listed
for that response and that citation's ``content`` is non-empty.

The citing sentence. The response is split into sentences at ``.``, ``!`` or ``?``
followed by whitespace and an upper-case letter, a digit-free opening bracket or a
quotation mark, and at blank lines; the abbreviations in ``ABBREVIATIONS`` (``et al.``,
``e.g.``, ``i.e.`` ...) never end a sentence. The claim is that sentence with every
inline citation and every parenthesis that held only citations removed.

The cited passage. A sentence's claim is attributed jointly to the citations it carries,
so each citation in a sentence is checked against the concatenated passages of all the
resolved citations in that sentence.

Checks per inline citation: resolution; W1 (a number in the claim absent from the
passages) and W2 (an assertive claim over hedged passages), both from
``consilience_ai2.receipts.claims``; and, for each quoted span of three or more words in
the sentence (inside straight or curly double quotes), an E6-style verbatim check against
the passages after the normalisation of ``core.normalise`` (``FOUND`` or
``NOT_FOUND``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from consilience_ai2.core.normalise import find_normalised
from consilience_ai2.core.numbers import NumberToken, extract_numbers
from consilience_ai2.receipts.claims import (
    CertaintyProfile,
    certainty_profile,
    certainty_upgrade,
    number_overreach,
)

INLINE = re.compile(r"(?<![\w\-'’])((?:\([^\s()]+\))|[^\s(),;\[\]]+) et al\. (?:\d{4}|None)[a-z]+\b")
ABBREVIATIONS = ("et al.", "e.g.", "i.e.", "vs.", "cf.", "etc.", "Fig.", "Figs.", "Eq.",
                 "Eqs.", "approx.", "Ref.", "Refs.", "No.", "al.", "Dr.", "Mr.", "Ms.", "St.")
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(\[])|\n\s*\n")
_ONLY_CITES = re.compile(r"\(\s*(?:[;,]\s*)*\)")
_QUOTED = re.compile(r"[\"“]([^\"“”]{3,}?)[\"”]")
MIN_QUOTE_WORDS = 3


@dataclass(frozen=True)
class Sentence:
    start: int
    end: int
    text: str


def split_sentences(text: str) -> list[Sentence]:
    """Sentences of ``text`` with their offsets (see the module docstring)."""
    out: list[Sentence] = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        before = text[start:m.start()]
        blank_line = m.group(0).count("\n") >= 2
        if not blank_line and any(before.endswith(a) for a in ABBREVIATIONS):
            continue
        if before.strip():
            out.append(Sentence(start, m.start(), before))
        start = m.end()
    if text[start:].strip():
        out.append(Sentence(start, len(text), text[start:]))
    return out


def claim_text(sentence: str) -> str:
    """The sentence with its inline citations (and the parentheses that held only
    citations) removed, whitespace collapsed."""
    t = INLINE.sub(" ", sentence)
    t = _ONLY_CITES.sub(" ", t)
    return " ".join(t.split())


@dataclass
class CitationResult:
    vote_index: int
    side: str  # "A" or "B"
    marker: str
    start: int
    end: int
    resolved: bool
    passage_index: int | None
    w1: bool | None = None  # None when the citation is unresolved (nothing to compare)
    w2: bool | None = None
    unsupported_numbers: list[str] = field(default_factory=list)
    claim: str = ""
    sentence_start: int = 0
    sentence_end: int = 0
    w2_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuoteResult:
    vote_index: int
    side: str
    text: str
    start: int
    end: int
    outcome: str  # FOUND or NOT_FOUND
    passage_index: int | None = None
    passage_offset: tuple[int, int] | None = None


@dataclass
class ResponseResult:
    vote_index: int
    side: str
    citations: list[CitationResult] = field(default_factory=list)
    quotes: list[QuoteResult] = field(default_factory=list)

    @property
    def n_citations(self) -> int:
        return len(self.citations)

    @property
    def n_flagged(self) -> int:
        return sum(1 for c in self.citations if c.w1 or c.w2)

    def flag_rate(self) -> float | None:
        return self.n_flagged / self.n_citations if self.citations else None


class PassageCache:
    """Number tokens and certainty profiles per passage text, computed once."""

    def __init__(self) -> None:
        self._tokens: dict[str, list[NumberToken]] = {}
        self._profiles: dict[str, CertaintyProfile] = {}

    def tokens(self, texts: list[str]) -> list[NumberToken]:
        out: list[NumberToken] = []
        for t in texts:
            if t not in self._tokens:
                self._tokens[t] = extract_numbers(t)
            out.extend(self._tokens[t])
        return out

    def profile(self, texts: list[str]) -> CertaintyProfile:
        h: list[str] = []
        a: list[str] = []
        n: list[str] = []
        for t in texts:
            if t not in self._profiles:
                self._profiles[t] = certainty_profile(t)
            p = self._profiles[t]
            h.extend(p.hedged)
            a.extend(p.assertive)
            n.extend(p.negated_assertive)
        return CertaintyProfile(tuple(h), tuple(a), tuple(n))


def _passage_text(c: Any) -> str | None:
    if isinstance(c, dict) and isinstance(c.get("content"), str) and c["content"].strip():
        return c["content"]
    return None


def check_response(vote_index: int, side: str, response: str, citations: list[Any],
                   cache: PassageCache | None = None) -> ResponseResult:
    """Resolution, W1, W2 and the verbatim check for one response."""
    cache = cache or PassageCache()
    by_key: dict[str, int] = {}
    for i, c in enumerate(citations):
        if isinstance(c, dict) and isinstance(c.get("concise_authors"), str):
            by_key.setdefault(c["concise_authors"], i)
    res = ResponseResult(vote_index, side)
    for s in split_sentences(response):
        markers = list(INLINE.finditer(s.text))
        quotes = [q for q in _QUOTED.finditer(s.text)
                  if len(q.group(1).split()) >= MIN_QUOTE_WORDS]
        if not markers and not quotes:
            continue
        claim = claim_text(s.text)
        idx: list[int | None] = []
        for m in markers:
            i = by_key.get(m.group(0))
            idx.append(i if i is not None and _passage_text(citations[i]) is not None else None)
        passages: list[str] = []
        pidx: list[int] = []
        for i in idx:
            if i is not None and i not in pidx:
                pidx.append(i)
                passages.append(_passage_text(citations[i]) or "")
        w1 = w2 = None
        unsupported: list[str] = []
        w2d: dict[str, Any] = {}
        if passages:
            c1 = number_overreach(claim, "", cache.tokens(passages))
            c2 = certainty_upgrade(claim, "", cache.profile(passages))
            w1, w2 = c1.flagged, c2.flagged
            unsupported = [t.text for t in c1.unsupported]
            w2d = c2.details() if c2.flagged else {}
        for m, i in zip(markers, idx, strict=True):
            res.citations.append(CitationResult(
                vote_index, side, m.group(0), s.start + m.start(), s.start + m.end(),
                i is not None, i, w1 if i is not None else None, w2 if i is not None else None,
                unsupported if i is not None else [], claim, s.start, s.end,
                w2d if i is not None else {}))
        if passages:
            for q in quotes:
                found = None
                for i, p in zip(pidx, passages, strict=True):
                    hits = find_normalised(q.group(1), p)
                    if hits:
                        found = (i, hits[0])
                        break
                res.quotes.append(QuoteResult(
                    vote_index, side, q.group(1), s.start + q.start(1), s.start + q.end(1),
                    "FOUND" if found else "NOT_FOUND",
                    found[0] if found else None, found[1] if found else None))
    return res


def check_vote(vote_index: int, vote: dict[str, Any],
               cache: PassageCache | None = None) -> tuple[ResponseResult, ResponseResult]:
    cache = cache or PassageCache()
    a = check_response(vote_index, "A", vote.get("responseA") or "",
                       vote.get("citations_a") or [], cache)
    b = check_response(vote_index, "B", vote.get("responseB") or "",
                       vote.get("citations_b") or [], cache)
    return a, b
