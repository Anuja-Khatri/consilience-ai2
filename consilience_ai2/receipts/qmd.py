"""Find the ``.ev`` spans in a Quarto (``.qmd``) file, as Pandoc would read them.

The Asta evidence filter (``_extensions/evidence/snippet.lua`` in asta-plugins) acts on
every Pandoc ``Span`` whose classes include ``ev``. In Markdown such a span is a
bracketed span: ``[content]{attributes}``, with the attribute block directly after the
closing bracket. The filter reads the attributes ``key``, ``quote``, ``cite``,
``source``, ``url`` and ``locator``; an empty value counts as absent.

This module reproduces that reading without running Pandoc:

- Code and comments are masked first (fenced code blocks, inline code, HTML comments
  and the YAML front matter), so an example span inside a code block is not a span.
- An attribute block is ``{`` then any of ``#id``, ``.class``, ``key=value``,
  ``key="value"`` or ``key='value'`` separated by whitespace (newlines included), then
  ``}``. Inside quotes a backslash escapes the next character. Anything else means it is
  not an attribute block.
- The span content is the text between the matching ``[`` (brackets balanced, ``\\[``
  and ``\\]`` escaped) and the ``]`` before the block. A ``]`` followed by ``(`` is a
  link, not a span, and is ignored, as is ``![...]`` (an image).

Each span carries its 1-based line (of the opening bracket), its offsets and its
attributes. ``plain_text`` turns span content into the text a reader sees, for W1 and
W2: nested attribute blocks, citations ``[@key]``, link targets and emphasis markers are
removed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})[^\n]*$", re.M)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_KEY = re.compile(r"[A-Za-z0-9_:\-][A-Za-z0-9_:.\-]*")
_IDENT = re.compile(r"[A-Za-z0-9_:\-][A-Za-z0-9_:.\-]*")


@dataclass(frozen=True)
class Span:
    """One bracketed span with its attributes, as read from a ``.qmd`` file."""

    line: int
    start: int  # offset of the opening '['
    end: int  # offset just after the closing '}'
    content: str
    content_start: int
    identifier: str | None
    classes: tuple[str, ...]
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def is_ev(self) -> bool:
        return "ev" in self.classes

    def attr(self, name: str) -> str | None:
        """The attribute value, or None when absent or empty (as the Lua filter reads it)."""
        v = self.attributes.get(name)
        return v if v else None


def _blank(chars: list[str], a: int, b: int) -> None:
    for i in range(a, b):
        if chars[i] != "\n":
            chars[i] = " "


def mask(text: str) -> str:
    """``text`` with front matter, fenced code, inline code and HTML comments blanked.

    Offsets and line breaks are preserved, so positions in the result are positions in
    the original.
    """
    chars = list(text)
    # YAML front matter at the very top
    if text.startswith("---\n") or text.startswith("---\r\n"):
        m = re.compile(r"^(?:---|\.\.\.)[ \t]*\r?$", re.M).search(text, 4)
        if m:
            _blank(chars, 0, m.end())
    # fenced code blocks
    pos = 0
    while True:
        m = _FENCE.search(text, pos)
        if not m:
            break
        fence = m.group(2)
        close = re.compile(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$",
                           re.M)
        c = close.search(text, m.end() + 1)
        stop = c.end() if c else len(text)
        _blank(chars, m.start(), stop)
        pos = stop
    masked = "".join(chars)
    # HTML comments
    for m in _COMMENT.finditer(masked):
        _blank(chars, m.start(), m.end())
    masked = "".join(chars)
    # inline code: a run of n backticks closed by a run of exactly n backticks
    i = 0
    n = len(masked)
    while i < n:
        if masked[i] != "`":
            i += 1
            continue
        j = i
        while j < n and masked[j] == "`":
            j += 1
        run = j - i
        k = j
        found = -1
        while k < n:
            if masked[k] == "`":
                e = k
                while e < n and masked[e] == "`":
                    e += 1
                if e - k == run:
                    found = e
                    break
                k = e
            else:
                k += 1
        if found == -1:
            i = j
            continue
        _blank(chars, i, found)
        i = found
    return "".join(chars)


def parse_attributes(text: str, pos: int) -> tuple[int, str | None, list[str], dict[str, str]] | None:
    """Parse a Pandoc attribute block starting at ``text[pos] == '{'``.

    Returns ``(end, identifier, classes, attributes)`` with ``end`` just after ``}``, or
    None when the text there is not an attribute block.
    """
    if pos >= len(text) or text[pos] != "{":
        return None
    i = pos + 1
    n = len(text)
    ident: str | None = None
    classes: list[str] = []
    attrs: dict[str, str] = {}
    while True:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i >= n:
            return None
        c = text[i]
        if c == "}":
            return i + 1, ident, classes, attrs
        if c == "#":
            m = _IDENT.match(text, i + 1)
            if not m:
                return None
            ident = m.group(0)
            i = m.end()
        elif c == ".":
            m = _IDENT.match(text, i + 1)
            if not m:
                return None
            classes.append(m.group(0))
            i = m.end()
        elif c == "-" and i + 1 < n and text[i + 1] in " \t\r\n}":
            classes.append("unnumbered")
            i += 1
        else:
            m = _KEY.match(text, i)
            if not m or m.end() >= n or text[m.end()] != "=":
                return None
            key = m.group(0)
            i = m.end() + 1
            if i < n and text[i] in "\"'":
                q = text[i]
                i += 1
                buf: list[str] = []
                while i < n and text[i] != q:
                    if text[i] == "\\" and i + 1 < n:
                        buf.append(text[i + 1])
                        i += 2
                        continue
                    buf.append(text[i])
                    i += 1
                if i >= n:
                    return None
                i += 1
                value = "".join(buf)
            else:
                j = i
                while j < n and text[j] not in " \t\r\n}":
                    j += 1
                value = text[i:j]
                i = j
            attrs.setdefault(key, value)
        if i < n and text[i] not in " \t\r\n}":
            return None


def _matching_open(text: str, close: int) -> int | None:
    """Offset of the '[' that the ']' at ``close`` closes, or None."""
    depth = 0
    i = close
    while i >= 0:
        c = text[i]
        escaped = i > 0 and text[i - 1] == "\\"
        if c == "]" and not escaped:
            depth += 1
        elif c == "[" and not escaped:
            depth -= 1
            if depth == 0:
                return i
        i -= 1
    return None


def find_spans(text: str, ev_only: bool = True) -> list[Span]:
    """Every bracketed span in ``text`` (only ``.ev`` spans when ``ev_only``), in order."""
    masked = mask(text)
    spans: list[Span] = []
    pos = 0
    while True:
        k = masked.find("]{", pos)
        if k == -1:
            break
        pos = k + 1
        if k > 0 and masked[k - 1] == "\\":
            continue
        parsed = parse_attributes(masked, k + 1)
        if parsed is None:
            continue
        end, ident, classes, _ = parsed
        if ev_only and "ev" not in classes:
            continue
        start = _matching_open(masked, k)
        if start is None or (start > 0 and masked[start - 1] == "!"):
            continue
        # attribute values are read from the original text: masking may have blanked a
        # backtick-quoted part of a value
        orig = parse_attributes(text, k + 1)
        attrs = orig[3] if orig is not None and orig[0] == end else parsed[3]
        spans.append(Span(
            line=text.count("\n", 0, start) + 1, start=start, end=end,
            content=text[start + 1:k], content_start=start + 1,
            identifier=ident, classes=tuple(classes), attributes=attrs,
        ))
    spans.sort(key=lambda s: s.start)
    return spans


_NESTED_ATTR = re.compile(r"\{[^{}]*\}")
_CITE = re.compile(r"\[[^\[\]]*@[^\[\]]*\]")
_LINK = re.compile(r"\]\([^()]*\)")
_EMPH = re.compile(r"(?<!\\)[*_]{1,3}")


def plain_text(content: str) -> str:
    """Span content as a reader sees it: no attribute blocks, citations, link targets,
    brackets or emphasis markers."""
    t = _NESTED_ATTR.sub("", content)
    t = _CITE.sub("", t)
    t = _LINK.sub("]", t)
    t = t.replace("[", "").replace("]", "")
    t = _EMPH.sub("", t)
    return " ".join(t.split())


def front_matter(text: str) -> tuple[str, int] | None:
    """The YAML front matter text and the 1-based line it starts on, if any."""
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        return None
    m = re.compile(r"^(?:---|\.\.\.)[ \t]*\r?$", re.M).search(text, 4)
    if not m:
        return None
    first_nl = text.index("\n")
    return text[first_nl + 1:m.start()], 2
