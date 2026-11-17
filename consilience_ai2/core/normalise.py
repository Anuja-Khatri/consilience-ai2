"""Text normalisation for verbatim checks, with an offset map back to the original.

A quote copied from a PDF rarely matches the source byte for byte: ligatures, curly
quotes, hyphenation at line breaks and runs of whitespace differ. This module defines
ONE fixed normalisation, applied identically to the quote and to the source, so a
verbatim check can say FOUND or NOT_FOUND without judgement. It never changes words,
case, digits or punctuation other than what is listed here.

The steps, in the order ``normalise`` applies them (each is a public, tested function):

1. ``expand_ligatures``: the Latin typographic ligatures U+FB00 to U+FB06 become their
   letters (``ﬁ`` -> ``fi``, ``ﬄ`` -> ``ffl``, ``ﬆ`` -> ``st``).
2. ``nfkc_safe``: Unicode NFKC, but only where it cannot change a number or a symbol's
   meaning. A character is replaced by its NFKC form only when its compatibility
   decomposition is tagged ``<compat>``, ``<font>``, ``<wide>``, ``<narrow>``,
   ``<noBreak>``, ``<small>``, ``<vertical>``, ``<initial>``, ``<medial>``, ``<final>`` or
   ``<isolated>`` (for example a no-break space becomes a space, ``Ｆ`` becomes ``F``,
   ``…`` becomes ``...``). Superscripts, subscripts, vulgar fractions, circled and
   squared forms are kept (``x²`` stays ``x²``, ``½`` stays ``½``): NFKC would turn
   ``10⁻³`` into ``10-3``. Canonical composition (NFC) is then applied to each base
   character with its combining marks.
3. ``straighten_quotes``: the typographic quotes U+2018 to U+201B become ``'`` and
   U+201C to U+201F become ``"``. Primes (U+2032, U+2033) and guillemets are kept.
4. ``dehyphenate_line_breaks``: a hyphen (``-``, U+2010 or a soft hyphen U+00AD) that
   directly follows a letter and is followed, after optional spaces or tabs, by a line
   break and then a lowercase letter is removed together with the line break and the
   spaces around it (``exam-\\nple`` -> ``example``). A genuine compound split across a
   line (``self-\\nconsistent``) is joined too (``selfconsistent``); the rule is applied
   to both sides of a comparison, so it is consistent, not lossless.
5. ``strip_invisible``: remaining soft hyphens and the zero-width characters U+200B,
   U+200C, U+200D, U+2060 and U+FEFF are removed.
6. ``collapse_whitespace``: every run of Unicode whitespace becomes one space, and
   leading and trailing whitespace is removed.

``normalise_with_map(text)`` returns the normalised text and an ``OffsetMap``: for each
normalised character, the half-open span ``[start, end)`` of the original characters it
came from. ``OffsetMap.to_original(a, b)`` maps a normalised span back to the original,
so a receipt can quote the source exactly as stored. ``find_normalised`` searches a
normalised needle in a normalised haystack and returns original spans.

``NORMALISATION_VERSION`` names this exact rule set. It is recorded in every receipt;
any change to the steps or their order must change it.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

NORMALISATION_VERSION = "consilience-ai2.normalise/1"

# A spanned text: one (character, start, end) per character, where [start, end) is the
# span of ORIGINAL characters this character derives from.
_Spanned = list[tuple[str, int, int]]

LIGATURES: dict[str, str] = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "st",  # long s + t
    "ﬆ": "st",
}

NFKC_SAFE_TAGS = frozenset({
    "<compat>", "<font>", "<wide>", "<narrow>", "<noBreak>", "<small>", "<vertical>",
    "<initial>", "<medial>", "<final>", "<isolated>",
})

QUOTES: dict[str, str] = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
}

HYPHENS = "-‐­"
INVISIBLE = frozenset({"­", "​", "‌", "‍", "⁠", "﻿"})


# --------------------------------------------------------------------------- spanned


def _spanned(text: str) -> _Spanned:
    return [(c, i, i + 1) for i, c in enumerate(text)]


def _plain(chars: _Spanned) -> str:
    return "".join(c for c, _, _ in chars)


def _map_chars(chars: _Spanned, fn: Callable[[str], str]) -> _Spanned:
    """Replace each character by ``fn(char)`` (0, 1 or more characters), each inheriting
    the span of the character it replaced."""
    out: _Spanned = []
    for c, s, e in chars:
        for r in fn(c):
            out.append((r, s, e))
    return out


# --------------------------------------------------------------------------- steps


def _s_expand_ligatures(chars: _Spanned) -> _Spanned:
    return _map_chars(chars, lambda c: LIGATURES.get(c, c))


def _nfkc_char(c: str) -> str:
    decomp = unicodedata.decomposition(c)
    if decomp.startswith("<"):
        tag = decomp.split(" ", 1)[0]
        if tag in NFKC_SAFE_TAGS:
            return unicodedata.normalize("NFKC", c)
    return c


def _s_nfkc_safe(chars: _Spanned) -> _Spanned:
    chars = _map_chars(chars, _nfkc_char)
    # Canonical composition per cluster: a base character plus following combining marks.
    out: _Spanned = []
    i = 0
    n = len(chars)
    while i < n:
        j = i + 1
        while j < n and unicodedata.combining(chars[j][0]):
            j += 1
        cluster = chars[i:j]
        text = _plain(cluster)
        composed = unicodedata.normalize("NFC", text)
        if composed == text:
            out.extend(cluster)
        else:
            s, e = cluster[0][1], cluster[-1][2]
            out.extend((r, s, e) for r in composed)
        i = j
    return out


def _s_straighten_quotes(chars: _Spanned) -> _Spanned:
    return _map_chars(chars, lambda c: QUOTES.get(c, c))


_HYPHEN_BREAK = re.compile(r"(?<=[^\W\d_])[" + HYPHENS + r"][ \t]*\r?\n[ \t]*(?=[^\W\d_])")


def _s_dehyphenate(chars: _Spanned) -> _Spanned:
    text = _plain(chars)
    drop: set[int] = set()
    for m in _HYPHEN_BREAK.finditer(text):
        nxt = text[m.end()] if m.end() < len(text) else ""
        if nxt and nxt.islower():
            drop.update(range(m.start(), m.end()))
    if not drop:
        return chars
    return [ch for k, ch in enumerate(chars) if k not in drop]


def _s_strip_invisible(chars: _Spanned) -> _Spanned:
    return [ch for ch in chars if ch[0] not in INVISIBLE]


def _s_collapse_whitespace(chars: _Spanned) -> _Spanned:
    out: _Spanned = []
    run_start: int | None = None
    run_end = 0
    for c, s, e in chars:
        if c.isspace():
            if run_start is None:
                run_start = s
            run_end = e
            continue
        if run_start is not None:
            if out:  # interior run -> one space; a leading run is dropped
                out.append((" ", run_start, run_end))
            run_start = None
        out.append((c, s, e))
    # a trailing run is dropped
    return out


# (public name, spanned implementation) in application order
STEPS: tuple[tuple[str, Callable[[_Spanned], _Spanned]], ...] = (
    ("expand_ligatures", _s_expand_ligatures),
    ("nfkc_safe", _s_nfkc_safe),
    ("straighten_quotes", _s_straighten_quotes),
    ("dehyphenate_line_breaks", _s_dehyphenate),
    ("strip_invisible", _s_strip_invisible),
    ("collapse_whitespace", _s_collapse_whitespace),
)


def expand_ligatures(text: str) -> str:
    """Step 1: Latin typographic ligatures (U+FB00..U+FB06) to letters."""
    return _plain(_s_expand_ligatures(_spanned(text)))


def nfkc_safe(text: str) -> str:
    """Step 2: NFKC for meaning-preserving compatibility forms only, then NFC."""
    return _plain(_s_nfkc_safe(_spanned(text)))


def straighten_quotes(text: str) -> str:
    """Step 3: curly single and double quotes to ASCII ``'`` and ``"``."""
    return _plain(_s_straighten_quotes(_spanned(text)))


def dehyphenate_line_breaks(text: str) -> str:
    """Step 4: remove a hyphen + line break between a letter and a lowercase letter."""
    return _plain(_s_dehyphenate(_spanned(text)))


def strip_invisible(text: str) -> str:
    """Step 5: remove soft hyphens and zero-width characters."""
    return _plain(_s_strip_invisible(_spanned(text)))


def collapse_whitespace(text: str) -> str:
    """Step 6: whitespace runs to one space; trim both ends."""
    return _plain(_s_collapse_whitespace(_spanned(text)))


# --------------------------------------------------------------------------- map


@dataclass(frozen=True)
class OffsetMap:
    """For normalised character ``i``, ``starts[i]``..``ends[i]`` is its original span."""

    starts: tuple[int, ...]
    ends: tuple[int, ...]
    original_length: int

    def __len__(self) -> int:
        return len(self.starts)

    def to_original(self, start: int, end: int) -> tuple[int, int]:
        """Map the normalised half-open span ``[start, end)`` to an original span.

        The result covers every original character that contributed to the normalised
        span, including characters removed in between (a dropped hyphen, a collapsed
        whitespace run). An empty span maps to an empty span at the matching position.
        """
        n = len(self.starts)
        if not (0 <= start <= end <= n):
            raise IndexError(f"span [{start}, {end}) outside normalised length {n}")
        if start == end:
            pos = self.starts[start] if start < n else self.original_length
            return pos, pos
        return self.starts[start], self.ends[end - 1]


def normalise_with_map(text: str) -> tuple[str, OffsetMap]:
    """Apply every step in order; return the normalised text and its ``OffsetMap``."""
    chars = _spanned(text)
    for _, step in STEPS:
        chars = step(chars)
    return _plain(chars), OffsetMap(
        starts=tuple(s for _, s, _ in chars),
        ends=tuple(e for _, _, e in chars),
        original_length=len(text),
    )


def normalise(text: str) -> str:
    """The normalised text (``normalise_with_map(text)[0]``)."""
    return normalise_with_map(text)[0]


def find_normalised(needle: str, haystack: str) -> list[tuple[int, int]]:
    """Every occurrence of ``needle`` in ``haystack`` after normalising both.

    Returns original ``(start, end)`` spans in ``haystack``, in order, non-overlapping.
    An empty normalised needle matches nothing (an empty quote is never "found").
    """
    n_needle = normalise(needle)
    if not n_needle:
        return []
    n_hay, omap = normalise_with_map(haystack)
    spans: list[tuple[int, int]] = []
    pos = n_hay.find(n_needle)
    while pos != -1:
        spans.append(omap.to_original(pos, pos + len(n_needle)))
        pos = n_hay.find(n_needle, pos + len(n_needle))
    return spans
