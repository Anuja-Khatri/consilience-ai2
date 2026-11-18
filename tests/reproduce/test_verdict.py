"""V1 verdict from the numbers: every row of both decision tables, and the aggregate."""

from __future__ import annotations

import pytest

from consilience_ai2.reproduce import OUTCOMES, VERDICT_OF, aggregate, evaluate


def v1(rec, backend="fallback", rule="v0.2"):
    rep = evaluate(rec, backend=backend, skip=("P1",), rule=rule)
    f = next(x for x in rep.findings if x.code == "V1")
    return f, rep.extra["verdict"]


def label(rec, backend="fallback", rule="v0.2"):
    v = v1(rec, backend, rule)[1]
    return v["outcome_label"], v["verdict"]


def test_supported(record):
    assert label(record()) == ("supported", "reproduced")


def test_substitution_is_not_a_reproduction(record):
    assert label(record(quantity_mapping={"relation": "substitution"})) == \
        ("not_a_reproduction", "inconclusive")


def test_not_comparable(record):
    assert label(record(reproduction={"conditions": {"method": "OLS"}})) == \
        ("undecided(not_comparable)", "inconclusive")


def test_proxy_carries_a_caveat(record):
    f, v = v1(record(quantity_mapping={"relation": "proxy", "note": "self-report"}))
    assert v["verdict"] == "reproduced" and v["caveats"] == ["proxy: self-report"]


@pytest.mark.parametrize("over,reason", [
    ({"reproduction": {"n": 30}}, "underpowered"),
    ({"reproduction": {"status": "no_data"}}, "no_data"),
    ({"identifiability": {"identifiable": False}}, "not_identifiable"),
    ({"source": {"effect_size": {"value": 0}}}, "uncheckable"),
])
def test_not_decidable_is_undecided_even_when_significant(record, over, reason):
    assert label(record(over), rule="v0.1") == (f"undecided({reason})", "inconclusive")
    # v0.2: a zero source effect is a source that claims no effect
    want = "source_null" if reason == "uncheckable" else reason
    assert label(record(over)) == (f"undecided({want})", "inconclusive")


def test_opposite_effect(record):
    rec = record(reproduction={"value": -0.3, "effect_size": {"value": -0.3}, "p": 0.0001})
    assert label(rec) == ("opposite_effect", "not_reproduced")


@pytest.mark.parametrize("rep", [
    {"value": 0.05, "effect_size": {"value": 0.05}, "p": 0.01},   # significant, too small
    {"value": 0.12, "effect_size": {"value": 0.12}, "p": 0.11},   # big enough, not significant
])
def test_favorable_estimate_missing_the_threshold_is_undecided(record, rep):
    assert label(record(reproduction=rep)) == ("undecided(misses_threshold)", "inconclusive")


def null(record, **over):
    rec = record({"reproduction": {"value": 0.01, "effect_size": {"value": 0.01}, "p": 0.89}})
    rec.update(over)  # replace, do not merge (a positive control is given whole)
    return rec


def test_rejected_needs_a_passing_positive_control(record):
    assert label(null(record)) == ("rejected", "not_reproduced")
    assert label(null(record, positive_control={"p": 0.2})) == \
        ("undecided(positive_control_failed)", "inconclusive")
    assert label(null(record, positive_control={"passed": True})) == ("rejected", "not_reproduced")
    assert label(null(record, positive_control={"passed": False})) == \
        ("undecided(positive_control_failed)", "inconclusive")
    rec = null(record)
    del rec["positive_control"]
    assert label(rec) == ("undecided(no_positive_control)", "inconclusive")


def test_positive_control_number_wins_over_flag(record):
    f, v = v1(null(record, positive_control={"p": 0.2, "passed": True}))
    assert v["outcome_label"] == "undecided(positive_control_failed)"
    assert f.details["passed_flag_disagrees_with_p"] is True


def test_positive_control_without_numbers(record):
    f, v = v1(null(record, positive_control={"note": "ran"}))
    assert v["outcome_label"] == "undecided(no_positive_control)"


def test_negative_estimate_in_a_positive_hypothesis_is_a_null(record):
    rec = null(record)
    rec["reproduction"].update(value=-0.04, effect_size={"type": "r", "value": -0.04}, p=0.6)
    assert label(rec) == ("rejected", "not_reproduced")


def test_inconsistent_numbers(record):
    rec = record(reproduction={"value": 0.0, "effect_size": {"value": 0.0}, "p": 0.001})
    assert label(rec) == ("undecided(inconsistent_numbers)", "inconclusive")


def test_unreadable_threshold(record):
    rec = record(positive_control={"p": "0,1"})
    assert label(rec) == ("undecided(unreadable positive_control.p)", "inconclusive")


def test_p_computed_from_effect_and_n(record):
    rec = record()
    del rec["reproduction"]["p"]
    f, v = v1(rec)
    assert v["verdict"] == "reproduced"
    assert f.details["p_from"] == "computed from effect size and n"


def test_no_test(record):
    # value scale, no p, and a reproduction effect size without a value: nothing to test
    rec = record(thresholds={"minimum_effect_scale": "value"})
    del rec["reproduction"]["p"]
    rec["reproduction"]["effect_size"] = {"type": "r"}
    assert label(rec) == ("undecided(no_test)", "inconclusive")


def test_p_computed_for_proportions(record):
    rec = record(source={"effect_size": {"type": "h", "value": 0.4}, "n": 400},
                 reproduction={"effect_size": {"type": "h", "value": 0.35}, "n": 400})
    del rec["reproduction"]["p"]
    f, v = v1(rec)
    assert v["verdict"] == "reproduced" and f.details["p_from"].startswith("computed")


def test_direction_declared_and_missing(record):
    # v0.1: the declared direction decides; v0.2: the source's sign does
    rec = record(direction="negative")
    assert label(rec, rule="v0.1") == ("opposite_effect", "not_reproduced")
    f, v = v1(rec)
    assert v["verdict"] == "reproduced"
    assert f.details["declared_direction_disagrees_with_source"] is True
    rec = record(source={"value": 0, "effect_size": {"value": 0}})
    assert label(rec, rule="v0.1")[0] == "undecided(uncheckable)"
    assert label(rec)[0] == "undecided(source_null)"


def test_value_scale_with_units(record):
    rec = record(thresholds={"minimum_effect": 2, "minimum_effect_scale": "value"},
                 source={"value": 5.0, "unit": "%"}, reproduction={"value": 0.04,
                                                                  "unit": "dimensionless"})
    f, v = v1(rec)  # 0.04 = 4 %, below the 2 % minimum? no: 4 >= 2
    assert v["verdict"] == "reproduced" and f.details["effect"] == 4.0
    rec["reproduction"]["value"] = 0.01   # 1 % < 2 %
    assert label(rec)[0] == "undecided(misses_threshold)"


def test_value_scale_needs_a_value(record):
    rec = record(thresholds={"minimum_effect": 0.1, "minimum_effect_scale": "value"})
    del rec["reproduction"]["value"]
    del rec["source"]["value"]
    assert label(rec, rule="v0.1")[0] == "undecided(no_reproduction_value)"
    assert label(rec)[0] == "undecided(no_source_effect)"   # v0.2 reads the source first


def test_effect_scale_needs_an_effect(record):
    rec = record()
    rec["reproduction"]["effect_size"] = {"type": "r"}
    rec["source"]["effect_size"] = {"type": "r", "value": 0.31}
    assert label(rec)[0] == "undecided(no_reproduction_effect)"


# ----------------------------------------------------------------- equivalence mode
def eq(record, value, se=0.0021, unit="V", **over):
    rec = record(over)
    rec["thresholds"] = {"alpha": 0.05, "equivalence_margin": 0.01}
    rec["source"] = {"quantity": "potential", "value": 0.512, "unit": "V", "n": 12,
                     "conditions": {"cohort": "A"}}
    rec["reproduction"] = {"quantity": "potential", "value": value, "unit": unit, "n": 15,
                           "conditions": {"cohort": "B"}}
    if se is not None:
        rec["reproduction"]["se"] = se
    rec.pop("positive_control")
    return rec


def test_equivalence_supported(record):
    assert label(eq(record, 0.509)) == ("supported", "reproduced")


def test_equivalence_rejected_not_equivalent(record):
    assert label(eq(record, 0.47)) == ("rejected", "not_reproduced")
    assert v1(eq(record, 0.47))[1]["reason"] == "not_equivalent"


def test_equivalence_opposite(record):
    assert label(eq(record, -0.3)) == ("opposite_effect", "not_reproduced")


def test_equivalence_overlap(record):
    assert label(eq(record, 0.521)) == ("undecided(interval_overlaps_margin)", "inconclusive")


def test_equivalence_no_interval(record):
    assert label(eq(record, 0.509, se=None))[0] == "undecided(uncheckable)"


def test_equivalence_ci_instead_of_se(record):
    rec = eq(record, 0.509, se=None)
    rec["reproduction"].update(ci=[0.505, 0.513], ci_level=0.95)
    assert label(rec) == ("supported", "reproduced")


def test_equivalence_needs_units_to_convert(record):
    rec = eq(record, 509, se=2.1, unit="mV")
    assert label(rec, "fallback")[0] == "undecided(not_comparable)"


def test_equivalence_converts_units_with_consilience(record):
    pytest.importorskip("consilience")
    assert label(eq(record, 509, se=2.1, unit="mV"), "consilience") == ("supported", "reproduced")


# ----------------------------------------------------------------- prose vs numbers
def test_reported_verdict_compared_never_used(record):
    f, v = v1(record(reported_verdict="supported"))
    assert f.severity == "info" and f.details["reported_agrees"] is True
    f, v = v1(record(reproduction={"n": 30}, reported_verdict="supported"))
    assert v["verdict"] == "inconclusive"
    assert f.severity == "warning" and "the reported verdict says supported" in f.message
    # prose fields never change the verdict
    assert label(record(notes="This clearly failed to reproduce.")) == ("supported", "reproduced")


def test_v1_never_changes_the_exit_code(record):
    for rec in (record(), null(record), record(reproduction={"n": 30})):
        rep = evaluate(rec, backend="fallback", skip=("P1",))
        assert rep.exit_code() == 0


# ----------------------------------------------------------------------- aggregate
@pytest.mark.parametrize("parts,expected", [
    (["supported", "supported"], "supported"),
    (["supported", "rejected"], "partly_supported"),
    (["supported", "undecided"], "partly_supported"),
    (["supported", "opposite_effect"], "opposite_effect"),
    (["rejected", "rejected"], "rejected"),
    (["rejected", "undecided"], "undecided"),
    ([], "undecided"),
])
def test_aggregate(parts, expected):
    assert aggregate(parts) == expected


def test_aggregate_refuses_unknown():
    with pytest.raises(ValueError):
        aggregate(["great"])


def test_verdict_mapping_is_total():
    assert set(VERDICT_OF) == set(OUTCOMES)
    assert VERDICT_OF["partly_supported"] == "inconclusive"


# --- v0.2: the expected direction is the source's -------------------------------------

@pytest.mark.parametrize("src_r,rep_r,want", [
    (0.31, 0.27, ("supported", "reproduced")),             # positive source, same sign
    (-0.31, -0.27, ("supported", "reproduced")),           # negative source, same sign
    (-0.31, 0.27, ("opposite_effect", "not_reproduced")),  # negative source, other sign
    (0.31, -0.27, ("opposite_effect", "not_reproduced")),  # positive source, other sign
])
def test_v02_direction_is_the_source_sign(record, src_r, rep_r, want):
    rec = record(source={"value": src_r, "effect_size": {"value": src_r}},
                 reproduction={"value": rep_r, "effect_size": {"value": rep_r}})
    assert label(rec) == want


def test_v02_declared_direction_does_not_override_the_source(record):
    rec = record(direction="positive", source={"value": -0.31, "effect_size": {"value": -0.31}},
                 reproduction={"value": 0.27, "effect_size": {"value": 0.27}})
    assert label(rec, rule="v0.1") == ("supported", "reproduced")
    assert label(rec) == ("opposite_effect", "not_reproduced")


@pytest.mark.parametrize("over", [
    {"source": {"p": 0.2}},                                       # non-significant source
    {"source": {"value": 0.05, "effect_size": {"value": 0.05}}},  # below the minimum effect
    {"source": {"value": 0, "effect_size": {"value": 0}}},        # zero
])
def test_v02_source_null_is_undecided_in_minimum_effect_mode(record, over):
    f, v = v1(record(over))
    assert (v["outcome_label"], v["verdict"]) == ("undecided(source_null)", "inconclusive")
    assert f.details["source_claims_effect"] is False


def test_v02_source_null_in_equivalence_mode_is_judged_by_tost(record, delete):
    rec = record(thresholds={"minimum_effect": delete, "equivalence_margin": 0.1},
                 source={"value": 0.02, "effect_size": {"value": 0.02}, "p": 0.8},
                 reproduction={"value": 0.01, "effect_size": {"value": 0.01}, "se": 0.02,
                               "n": 2000})
    assert label(rec) == ("supported", "reproduced")
    assert label(rec, rule="v0.1") == ("supported", "reproduced")
    rec["reproduction"]["value"] = 0.3      # wholly outside the margin: not equivalent
    assert label(rec) == ("rejected", "not_reproduced")


def test_v02_one_sided_p_complement(record):
    # one-sided p's are in the declared direction; the source is negative, so 1 - p
    base = {"direction": "positive", "thresholds": {"sides": 1},
            "source": {"value": -0.31, "effect_size": {"value": -0.31}, "p": 0.999},
            "reproduction": {"value": -0.27, "effect_size": {"value": -0.27}, "p": 0.998}}
    f, v = v1(record(base))
    assert v["verdict"] == "reproduced"
    assert f.details["source_p_from"].startswith("record, one-sided complement")
    assert f.details["p"] == pytest.approx(0.002)
    # a source that is not significant in its own direction claims no effect
    assert label(record(base, source={"p": 0.5}))[0] == "undecided(source_null)"


def test_v02_source_p_computed_when_absent(record, delete):
    f, v = v1(record(source={"p": delete}))
    assert v["verdict"] == "reproduced"
    assert f.details["source_p_from"] == "computed from effect size and n"
    rec = record(source={"p": delete, "n": delete})
    assert label(rec)[0] == "undecided(no_source_test)"


def test_v02_no_data_before_source_null(record):
    rec = record(source={"p": 0.5}, reproduction={"status": "no_data"})
    assert label(rec)[0] == "undecided(no_data)"


def test_unknown_rule_refused(record):
    with pytest.raises(ValueError):
        evaluate(record(), backend="fallback", skip=("P1",), rule="v9")


def test_cli_rule_option(record, tmp_path, capsys):
    import json

    import yaml

    from consilience_ai2.cli import main
    path = tmp_path / "r.yaml"
    path.write_text(yaml.safe_dump(record(direction="negative")), encoding="utf-8")
    for rule, want in (("v0.1", "not_reproduced"), ("v0.2", "reproduced")):
        main(["reproduce", "check", str(path), "--backend", "fallback", "--skip", "P1",
              "--rule", rule, "--json", "-"])
        out = json.loads(capsys.readouterr().out)
        assert out["verdict"]["verdict"] == want and out["verdict"]["verdict_rule"] == rule
