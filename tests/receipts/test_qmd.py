"""Reading .ev spans from .qmd text as Pandoc would."""

from __future__ import annotations

from consilience_ai2.receipts.qmd import (
    find_spans,
    front_matter,
    mask,
    parse_attributes,
    plain_text,
)


def test_basic_span_and_attributes():
    t = 'Text [90 tasks]{.ev key="k1" cite=abc2020 locator=\'p. 4\'} more.'
    (s,) = find_spans(t)
    assert s.content == "90 tasks"
    assert s.line == 1
    assert s.attributes == {"key": "k1", "cite": "abc2020", "locator": "p. 4"}
    assert t[s.start:s.end] == '[90 tasks]{.ev key="k1" cite=abc2020 locator=\'p. 4\'}'


def test_multiline_attributes_and_escapes():
    t = 'a\n[claim]{.ev\n  quote="He said \\"yes\\" {braces} ok"\n  cite="x"}\n'
    (s,) = find_spans(t)
    assert s.line == 2
    assert s.attr("quote") == 'He said "yes" {braces} ok'
    assert s.attr("cite") == "x"


def test_empty_value_counts_as_absent():
    (s,) = find_spans('[c]{.ev key="" quote=""}')
    assert s.attr("key") is None and s.attr("quote") is None


def test_classes_ids_and_non_ev_spans():
    t = '[a]{#x .note} [b]{.note .ev key=k} [c]{.evidence key=z}'
    spans = find_spans(t)
    assert [s.content for s in spans] == ["b"]
    assert spans[0].classes == ("note", "ev")
    assert len(find_spans(t, ev_only=False)) == 3
    assert find_spans('[d]{#id-1 - .ev}')[0].classes == ("unnumbered", "ev")


def test_nested_brackets_and_citations():
    t = 'x [*Lee* found [@lee2023] that]{.ev key=k}.'
    (s,) = find_spans(t)
    assert s.content == "*Lee* found [@lee2023] that"
    assert plain_text(s.content) == "Lee found that"


def test_nested_ev_spans_both_found():
    t = '[outer [inner]{.ev key=a} text]{.ev key=b}'
    spans = find_spans(t)
    assert [s.attr("key") for s in spans] == ["b", "a"]
    assert plain_text(spans[0].content) == "outer inner text"


def test_links_images_and_escaped_brackets_are_not_spans():
    assert find_spans('[text](http://x){.ev key=k}') == []
    assert find_spans('![alt]{.ev key=k}') == []
    assert find_spans('\\[not]{.ev key=k}') == []
    assert find_spans('[a \\] b]{.ev key=k}')[0].content == 'a \\] b'
    assert find_spans('text \\]{.ev key=k}') == []


def test_not_an_attribute_block():
    assert parse_attributes("{not valid!}", 0) is None
    assert parse_attributes('{.ev key="unterminated}', 0) is None
    assert parse_attributes("{.ev}", 0) == (5, None, ["ev"], {})
    assert find_spans("[a]{.ev key=k") == []
    assert find_spans("[a]{=html}") == []


def test_masking_code_comments_and_front_matter():
    t = ('---\ntitle: "[x]{.ev key=fm}"\n---\n\n'
         '```markdown\n[a]{.ev key=fenced}\n```\n\n'
         '~~~~\n[b]{.ev key=tilde}\n~~~~\n'
         'inline `[c]{.ev key=code}` and ``[d]{.ev key=`x`}``\n'
         '<!-- [e]{.ev key=comment} -->\n'
         '[real]{.ev key=real}\n')
    assert len(mask(t)) == len(t)
    assert mask(t).count("\n") == t.count("\n")
    (s,) = find_spans(t)
    assert s.attr("key") == "real"
    assert s.line == t[:s.start].count("\n") + 1


def test_unclosed_fence_masks_to_end():
    t = "```\n[a]{.ev key=k}\n"
    assert find_spans(t) == []


def test_plain_text_strips_markup():
    assert plain_text("**bold** _it_ [link](http://x) {.c}") == "bold it link"


def test_front_matter():
    assert front_matter("no front matter") is None
    fm = front_matter("---\na: 1\n---\nbody")
    assert fm == ("a: 1\n", 2)
    assert front_matter("---\nunterminated") is None
