import pytest

from consilience_ai2.core.normalise import (
    NORMALISATION_VERSION,
    STEPS,
    OffsetMap,
    collapse_whitespace,
    dehyphenate_line_breaks,
    expand_ligatures,
    find_normalised,
    nfkc_safe,
    normalise,
    normalise_with_map,
    straighten_quotes,
    strip_invisible,
)


def test_steps_are_named_and_ordered():
    assert [n for n, _ in STEPS] == [
        "expand_ligatures", "nfkc_safe", "straighten_quotes",
        "dehyphenate_line_breaks", "strip_invisible", "collapse_whitespace",
    ]
    assert NORMALISATION_VERSION.endswith("/1")


@pytest.mark.parametrize("raw,want", [
    ("eﬃcient", "efficient"),
    ("ﬁnd ﬂow ﬀ ﬄ ﬆ", "find flow ff ffl st"),
])
def test_expand_ligatures(raw, want):
    assert expand_ligatures(raw) == want


@pytest.mark.parametrize("raw,want", [
    ("a b", "a b"),            # no-break space (<noBreak>)
    ("Ｆ１", "F1"),         # fullwidth (<wide>)
    ("wait…", "wait..."),      # ellipsis (<compat>)
    ("µm", "μm"),         # micro sign -> Greek mu (<compat>)
    ("é", "é"),          # canonical composition
    ("10⁻³", "10⁻³"),  # superscripts kept: 10⁻³ is not 10-3
    ("x²", "x²"),
    ("½", "½"),           # vulgar fraction kept
    ("H₂O", "H₂O"),       # subscript kept
    ("①", "①"),           # circled digit kept
])
def test_nfkc_safe(raw, want):
    assert nfkc_safe(raw) == want


def test_straighten_quotes():
    assert straighten_quotes("“yes” ‘no’ „qua‟") == "\"yes\" 'no' \"qua\""
    assert straighten_quotes("5′ 6″ «x»") == "5′ 6″ «x»"


@pytest.mark.parametrize("raw,want", [
    ("exam-\nple", "example"),
    ("exam-  \r\n  ple", "example"),
    ("exam‐\nple", "example"),
    ("exam­\nple", "example"),
    ("self-\nconsistent", "selfconsistent"),   # documented: compounds are joined too
    ("COVID-\n19", "COVID-\n19"),               # digit after: kept
    ("well-\nKnown", "well-\nKnown"),           # uppercase after: kept
    ("a - \nb", "a - \nb"),                     # hyphen not attached to a letter
    ("in-line", "in-line"),                     # no line break: kept
])
def test_dehyphenate(raw, want):
    assert dehyphenate_line_breaks(raw) == want


def test_strip_invisible():
    assert strip_invisible("a​b­c﻿d⁠e‌‍") == "abcde"


def test_collapse_whitespace():
    assert collapse_whitespace("  a \t\n b c  ") == "a b c"
    assert collapse_whitespace("") == ""
    assert collapse_whitespace(" \n ") == ""


def test_normalise_pipeline():
    raw = "  The  “coﬀee” eﬀect is signif-\n  icant here. "
    assert normalise(raw) == 'The "coffee" effect is significant here.'


def test_offset_map_roundtrip_identity():
    text = "plain ascii text"
    norm, omap = normalise_with_map(text)
    assert norm == text
    assert omap.to_original(0, len(norm)) == (0, len(text))
    assert len(omap) == len(norm)


def test_offset_map_points_back_to_original():
    raw = "We  found “signiﬁ-\ncant” gains."
    norm, omap = normalise_with_map(raw)
    assert norm == 'We found "significant" gains.'
    i = norm.index("significant")
    s, e = omap.to_original(i, i + len("significant"))
    assert raw[s:e] == "signiﬁ-\ncant"
    # the collapsed double space maps to both original spaces
    j = norm.index(" found")
    assert omap.to_original(j, j + 1) == (2, 4)


def test_ligature_chars_share_the_ligature_span():
    raw = "oﬃce"
    norm, omap = normalise_with_map(raw)
    assert norm == "office"
    assert omap.to_original(1, 2) == (1, 2)  # 'f' -> the ligature
    assert omap.to_original(1, 4) == (1, 2)  # 'ffi' -> the ligature
    assert omap.to_original(4, 6) == (2, 4)


def test_empty_span_and_bounds():
    norm, omap = normalise_with_map("ab")
    assert omap.to_original(1, 1) == (1, 1)
    assert omap.to_original(2, 2) == (2, 2)
    with pytest.raises(IndexError):
        omap.to_original(0, 3)
    assert isinstance(omap, OffsetMap)


def test_find_normalised():
    hay = "Prior work  reports an  eﬀect of 0.42 (p < 0.01).\nThe eﬀect replicates."
    spans = find_normalised("effect", hay)
    assert [hay[s:e] for s, e in spans] == ["eﬀect", "eﬀect"]
    spans = find_normalised("work reports", hay)
    assert [hay[s:e] for s, e in spans] == ["work  reports"]
    assert find_normalised("  ", hay) == []
    assert find_normalised("absent", hay) == []


def test_deterministic():
    raw = "“Aﬁ” -\n x y"
    assert normalise_with_map(raw) == normalise_with_map(raw)
