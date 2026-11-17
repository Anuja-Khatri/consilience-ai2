"""W1 (number overreach) and W2 (certainty upgrade), each in both directions."""

from __future__ import annotations

import json
from importlib import resources

from consilience_ai2.core.numbers import extract_numbers
from consilience_ai2.receipts.claims import (
    certainty_profile,
    certainty_upgrade,
    certainty_words,
    is_year_like,
    number_overreach,
)

# ---- W1


def test_w1_flags_a_number_absent_from_the_source():
    c = number_overreach("accuracy rose to 91.2%", "accuracy of 87.5% was reported")
    assert c.flagged and [t.text for t in c.unsupported] == ["91.2%"]


def test_w1_passes_a_number_present_in_the_source():
    c = number_overreach("accuracy of 87.5%", "an accuracy of 87.5 % on the test set")
    assert not c.flagged and [t.text for t in c.supported] == ["87.5%"]


def test_w1_printed_precision_both_ways():
    # claim rounder than source: supported (87.5 rounds to 88 at the claim's precision)
    assert not number_overreach("about 88%", "87.5%").flagged
    # claim more precise than source: unsupported
    assert number_overreach("0.421", "0.42").flagged
    assert not number_overreach("0.42", "0.4213").flagged


def test_w1_percent_scaling_and_sign():
    assert not number_overreach("45% of cases", "a fraction of 0.45").flagged
    assert not number_overreach("a share of 0.45", "45% of cases").flagged
    assert not number_overreach("error fell by 0.3", "a change of -0.3").flagged
    assert number_overreach("45% of cases", "0.46").flagged


def test_w1_skips_years_and_ambiguous_tokens():
    c = number_overreach("in 2024 the value was 1,2", "nothing numeric here")
    assert not c.flagged
    assert [t.text for t in c.years_skipped] == ["2024"]
    assert [t.text for t in c.ambiguous] == ["1,2"]
    assert number_overreach("in 2024 it was 7", "nothing").flagged
    (tok,) = extract_numbers("2024.5")
    assert not is_year_like(tok)


def test_w1_identifiers_are_not_numbers():
    assert not number_overreach("see e595.3 and F1 and COVID-19", "no numbers").flagged


def test_w1_uncertainty_values_are_checked():
    assert not number_overreach("0.42 ± 0.03", "was 0.42 ± 0.03").flagged
    assert number_overreach("0.42 ± 0.05", "was 0.42 ± 0.03").flagged


def test_w1_large_values_do_not_crash():
    assert not number_overreach("1e40", "1e40").flagged
    assert number_overreach("0.25", "1e400").flagged


def test_w1_details_are_json():
    d = number_overreach("3 and 4", "3").details()
    json.dumps(d)
    assert d["unsupported"] == ["4"] and d["unsupported_offsets"] == [[6, 7]]


# ---- W2


def test_w2_flags_hedged_to_assertive():
    c = certainty_upgrade("Batch size causes the effect.", "The effect may be associated with batch size.")
    assert c.flagged
    assert c.details()["claim_assertive"] == ["causes"]
    assert c.details()["source_hedged"] == ["may", "associated"]


def test_w2_passes_hedged_claim_over_hedged_source():
    assert not certainty_upgrade("Batch size may matter.", "It may be associated.").flagged


def test_w2_passes_assertive_claim_over_assertive_source():
    assert not certainty_upgrade("It shows X.", "We show X, which may matter.").flagged


def test_w2_passes_assertive_claim_over_neutral_source():
    assert not certainty_upgrade("It proves X.", "We measured X.").flagged


def test_w2_claim_with_hedge_is_not_assertive():
    assert not certainty_upgrade("It may show X.", "It suggests X.").flagged


def test_w2_negation():
    p = certainty_profile("This does not prove anything; it doesn't show much.")
    assert p.assertive == () and p.negated_assertive == ("prove", "show")
    assert not certainty_upgrade("This does not prove X.", "It suggests X.").flagged
    # a negated assertive word in the source does not stop the source being hedged
    assert certainty_upgrade("It proves X.", "It may hold; we cannot prove it.").flagged
    # outside the window, the negator does not apply
    assert certainty_profile("not at all, it shows").assertive == ("shows",)


def test_w2_normalisation_and_case():
    p = certainty_profile("It SHOWS that “it” doesn’t prove; ﬁne")
    assert p.assertive == ("shows",) and p.negated_assertive == ("prove",)


def test_w2_whole_words_only():
    p = certainty_profile("showcase unlikely mayor")
    assert p.hedged == () and p.assertive == ()


def test_word_lists_are_versioned_disjoint_and_sorted():
    raw = json.loads(resources.files("consilience_ai2.receipts").joinpath(
        "data/certainty_words.json").read_text())
    cw = certainty_words()
    assert cw.version == raw["version"] and cw.version.startswith("consilience-ai2.certainty/")
    assert not (cw.hedged & cw.assertive)
    assert not (cw.negators & (cw.hedged | cw.assertive))
    for k in ("hedged", "assertive", "negators"):
        assert raw[k] == sorted(raw[k]) and len(set(raw[k])) == len(raw[k])
