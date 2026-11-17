"""The SciArena adapter on synthetic votes in the released format."""

from __future__ import annotations

from consilience_ai2.receipts import sciarena as sa


def cit(authors, content):
    return {"concise_authors": authors, "content": content, "title": "t", "authors": [],
            "id": "1"}


VOTE = {
    "responseA": ("Prior work found a 12% gain (Smith et al. 2020a). Others reported 40% "
                  "(Lee et al. 2021b; Smith et al. 2020a). The method causes the gain "
                  "(Ng et al. 2019a).\n\nA missing source says so (Ghost et al. 2018a). "
                  'As one paper put it, "the gain is robust across seeds" (Smith et al. 2020a). '
                  'It also "never happened in this text" (Lee et al. 2021b). No citation here.'),
    "responseB": "Nothing cited at all.",
    "citations_a": [cit("Smith et al. 2020a", "We found a 12% gain; the gain is robust across seeds."),
                    cit("Lee et al. 2021b", "Gains of 40% were reported."),
                    cit("Ng et al. 2019a", "The method may be associated with the gain."),
                    cit("Ghost et al. 2018a", "")],
    "citations_b": [],
    "vote": "A",
}


def test_sentences_and_claims():
    s = sa.split_sentences("One (Smith et al. 2020a). Two e.g. this. Three?\n\nfour.")
    assert [x.text for x in s] == ["One (Smith et al. 2020a).", "Two e.g. this.", "Three?",
                                   "four."]
    assert sa.claim_text("A gain (Smith et al. 2020a; Lee et al. 2021b) of 3.") == "A gain of 3."
    assert sa.claim_text("As (SOARE) et al. 2023a showed") == "As showed"
    assert [m.group(0) for m in sa.INLINE.finditer(
        "(Al-Hariby et al. 2015a, D’Amario et al. 2021a; Unknown et al. Nonea)")] == [
        "Al-Hariby et al. 2015a", "D’Amario et al. 2021a", "Unknown et al. Nonea"]
    assert not list(sa.INLINE.finditer("Hariby et al. 2015 and xAl-Hariby et al. 2015a"))[1:]


def test_citations_resolution_w1_w2():
    a, b = sa.check_vote(0, VOTE)
    assert b.citations == [] and b.flag_rate() is None
    got = [(c.marker, c.resolved, c.w1, c.w2) for c in a.citations]
    assert got == [
        ("Smith et al. 2020a", True, False, False),
        ("Lee et al. 2021b", True, False, False),   # 40% is in the joint passages
        ("Smith et al. 2020a", True, False, False),
        ("Ng et al. 2019a", True, False, True),     # causes over may/associated
        ("Ghost et al. 2018a", False, None, None),  # empty content: unresolved
        ("Smith et al. 2020a", True, False, False),
        ("Lee et al. 2021b", True, False, False),
    ]
    assert a.n_flagged == 1 and a.flag_rate() == 1 / 7


def test_w1_per_citation():
    v = {"responseA": "A gain of 15% (Lee et al. 2021b).", "citations_a": [
        cit("Lee et al. 2021b", "Gains of 40% were reported.")], "responseB": "", "citations_b": []}
    a, _ = sa.check_vote(1, v)
    (c,) = a.citations
    assert c.w1 and c.unsupported_numbers == ["15%"] and c.claim == "A gain of 15% ."


def test_quotes_verbatim():
    a, _ = sa.check_vote(0, VOTE)
    assert [(q.text, q.outcome) for q in a.quotes] == [
        ("the gain is robust across seeds", "FOUND"),
        ("never happened in this text", "NOT_FOUND")]
    found = a.quotes[0]
    content = VOTE["citations_a"][0]["content"]
    a0 = content.index("the gain is")
    assert found.passage_index == 0 and found.passage_offset == (a0, a0 + 31)


def test_unknown_marker_is_unresolved():
    v = {"responseA": "X (Smith et al. 2020b).", "citations_a": [cit("Smith et al. 2020a", "x")],
         "responseB": "", "citations_b": []}
    a, _ = sa.check_vote(2, v)
    assert [(c.resolved, c.w1) for c in a.citations] == [(False, None)]
