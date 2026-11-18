"""W1 and W2 rules v0.2, each change tested in both directions and against v0.1.

v0.1 is frozen (it scored the preregistered SciArena test); these tests pin where the two
versions differ and where they must agree.
"""

from __future__ import annotations

import json
from importlib import resources

import pytest

from consilience_ai2.receipts import check_workspace
from consilience_ai2.receipts.claims import (
    DEFAULT_RULES,
    certainty_profile,
    certainty_upgrade,
    certainty_words,
    number_overreach,
)
from consilience_ai2.receipts.numbers_w1 import extract_w1_numbers


def flagged(claim: str, source: str, rules: str = "v0.2") -> bool:
    return number_overreach(claim, source, rules=rules).flagged


def values(text: str) -> list[list[str]]:
    return [[str(r.value) for r in n.readings] for n in extract_w1_numbers(text)]


def test_default_is_v02():
    assert DEFAULT_RULES == "v0.2"
    with pytest.raises(ValueError):
        number_overreach("1", "1", rules="v9")


# ---- W1: number words


def test_number_words_support_and_flag():
    assert not flagged("three trials", "3 trials were run")
    assert flagged("three trials", "5 trials were run")
    assert not flagged("3 trials", "three trials were run")
    assert flagged("3 trials", "two trials were run")
    # v0.1 does not read words: no flag either way
    assert not flagged("three trials", "5 trials were run", "v0.1")
    assert flagged("3 trials", "three trials were run", "v0.1")


def test_number_word_phrases():
    assert values("two hundred and five, twenty-five, a thousand, one hundred") == [
        ["205"], ["25"], ["1000"], ["100"]]
    # a phrase ending in a multiplier has that multiplier's precision
    assert not flagged("two hundred cells", "214 cells")
    assert flagged("two hundred cells", "260 cells")
    assert flagged("two hundred and five cells", "214 cells")


def test_number_words_not_read():
    # "one" alone, compound modifiers, plurals, relations, coordinated words
    assert values("one of the methods; a two-stage, zero-shot model") == []
    assert values("hundreds of runs; several million; it doubled, twice, half") == []
    assert values("between two and three") == [["2"], ["3"]]
    assert not flagged("one of the two-stage models doubled accuracy", "accuracy rose")


# ---- W1: percent, scale, signs, powers


def test_percent_words_and_fraction_equivalence():
    assert not flagged("50 percent of patients", "a fraction of 0.5")
    assert not flagged("50 per cent of patients", "a fraction of 0.50")
    assert flagged("50 percent of patients", "a fraction of 0.6")
    assert not flagged("a fraction of 0.5", "50 percent of patients")
    # v0.1 reads "50 percent" as the plain number 50
    assert flagged("50 percent of patients", "a fraction of 0.5", "v0.1")


def test_scale_words_and_suffixes():
    assert not flagged("1.5 million users", "1,500,000 users")
    assert flagged("1.5 million users", "1,700,000 users")
    assert not flagged("1.5k users", "1500 users")
    assert flagged("1.5k users", "1.5 users")  # lower-case k is read as thousand only
    assert not flagged("a 7B model", "7 billion parameters")
    assert not flagged("a 2M solution", "2 molar")  # M is read both ways
    assert flagged("a 2M solution", "3 molar")
    assert not flagged("1.5kg", "1.5 kilograms") and flagged("1.5kg", "1500 grams")
    assert flagged("1.5 million users", "1,500,000 users", "v0.1")


def test_signs():
    assert flagged("a change of -0.3", "a change of +0.3")
    assert not flagged("a change of -0.3", "a change of \u22120.3")
    assert not flagged("a change of -0.3", "it fell by 0.3")  # unsigned source
    assert not flagged("it fell by 0.3", "a change of -0.3")  # unsigned claim
    assert not flagged("a change of -0.3", "a change of +0.3", "v0.1")


def test_powers_are_one_number():
    assert values("10^2, 10**2, 10^{-3}, 2^10, 10\u207b\u00b3") == [
        ["1E+2"], ["1E+2"], ["0.001"], ["1024"], ["0.001"]]
    assert not flagged("about 10^2 cells", "100 cells")
    assert flagged("about 10^3 cells", "100 cells")
    assert flagged("about 10^2 cells", "100 cells", "v0.1")  # v0.1 reads 10 and 2
    # the exponent of a symbol is not a quantity; mantissa x 10^k stays one number
    assert values("x^2 + y**3") == []
    assert values("1.5 \u00d7 10^-3") == [["0.0015"]]
    assert values("10^99") and not extract_w1_numbers("10^99")[0].ok


# ---- W2


def test_clause_bounded_negation():
    claim = "There is no evidence that this approach clearly causes harm."
    src = "It may lead to harm."
    assert not certainty_upgrade(claim, src, rules="v0.2").flagged
    assert certainty_upgrade(claim, src, rules="v0.1").flagged  # outside two words
    # the scope ends at punctuation and at a conjunction
    assert certainty_profile("No; it shows X.", rules="v0.2").assertive == ("shows",)
    assert certainty_profile("No; it shows X.", rules="v0.1").assertive == ()
    assert certainty_profile("It is not new but shows X.", rules="v0.2").assertive == ("shows",)
    # "or" stays inside the scope
    assert certainty_profile("It did not show or confirm X.", rules="v0.2").assertive == ()


def test_new_negators_boosters_and_hedges():
    assert certainty_profile("They failed to show it.", rules="v0.2").assertive == ()
    assert certainty_profile("They failed to show it.", rules="v0.1").assertive == ("show",)
    assert certainty_upgrade("X obviously drives Y.", "X may drive Y.", rules="v0.2").flagged
    assert not certainty_upgrade("X obviously drives Y.", "X may drive Y.", rules="v0.1").flagged
    assert certainty_upgrade("X causes Y.", "Whether X drives Y is unclear.", rules="v0.2").flagged
    assert not certainty_upgrade("X causes Y.", "Whether X drives Y is unclear.",
                                 rules="v0.1").flagged


def test_v2_extends_v1_and_documents_additions():
    v1, v2 = certainty_words("v0.1"), certainty_words("v0.2")
    assert v1.hedged <= v2.hedged and v1.assertive <= v2.assertive and v1.negators <= v2.negators
    raw = json.loads(resources.files("consilience_ai2.receipts").joinpath(
        "data/certainty_words_v2.json").read_text())
    added = {w for ws in raw["added"].values() for w in ws}
    new = (v2.hedged - v1.hedged) | (v2.assertive - v1.assertive) | (v2.negators - v1.negators)
    assert added == new


# ---- the workspace checker records the rules


def test_workspace_reports_rules(tmp_path):
    (tmp_path / "evidence.yml").write_text(
        'evidence:\n  k:\n    quote: "Three of five runs may fail."\n')
    (tmp_path / "a.qmd").write_text('[Seven runs clearly fail]{.ev key="k"}\n')
    r2 = check_workspace(tmp_path, rules="v0.2", with_w2=True)
    r1 = check_workspace(tmp_path, rules="v0.1", with_w2=True)
    assert r2.extra["rules"]["w1_w2_rules"] == "v0.2"
    assert r2.extra["rules"]["certainty_words"] == "consilience-ai2.certainty/2"
    assert r1.extra["rules"]["numbers"] == "consilience-ai2.w1/1"
    assert sorted(f.code for f in r2.findings if f.severity == "warning") == ["W1", "W2"]
    assert sorted(f.code for f in r1.findings if f.severity == "warning") == ["W2"]
