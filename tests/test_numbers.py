from decimal import Decimal

import pytest

from consilience_ai2.core.numbers import agrees_at_printed_precision, extract_numbers


def vals(text, **kw):
    return [(t.text, t.value, t.decimals, t.status) for t in extract_numbers(text, **kw)]


def one(text, **kw):
    toks = extract_numbers(text, **kw)
    assert len(toks) == 1, toks
    return toks[0]


def test_integers_and_decimals_with_spans():
    text = "n = 50 and r = 0.42, mean .5"
    toks = extract_numbers(text)
    assert [(t.text, t.value, t.decimals) for t in toks] == [
        ("50", Decimal("50"), 0), ("0.42", Decimal("0.42"), 2), (".5", Decimal("0.5"), 1)]
    for t in toks:
        assert text[t.start:t.end] == t.text


def test_trailing_zeros_keep_printed_precision():
    t = one("accuracy 24.0%")
    assert t.value == Decimal("24.0") and t.decimals == 1 and t.percent


@pytest.mark.parametrize("text,value,pct", [
    ("45%", Decimal("45"), True),
    ("45 %", Decimal("45"), True),
    (r"45.5\%", Decimal("45.5"), True),
    ("45", Decimal("45"), False),
])
def test_percent(text, value, pct):
    t = one(text)
    assert (t.value, t.percent) == (value, pct)


@pytest.mark.parametrize("text,value,decimals,exp", [
    ("1.5e-3", Decimal("0.0015"), 1, -3),
    ("1.5E+03", Decimal("1500"), 1, 3),
    ("2e5", Decimal("200000"), 0, 5),
    ("1.5 × 10^-3", Decimal("0.0015"), 1, -3),
    ("1.5 x 10^-3", Decimal("0.0015"), 1, -3),
    ("1.5*10**-3", Decimal("0.0015"), 1, -3),
    (r"1.5 \times 10^{-3}", Decimal("0.0015"), 1, -3),
    ("1.5×10⁻³", Decimal("0.0015"), 1, -3),
    ("3.0 · 10^{4}", Decimal("30000"), 1, 4),
])
def test_scientific(text, value, decimals, exp):
    t = one(text)
    assert t.value == value and t.decimals == decimals and t.exponent == exp
    assert t.text == text


def test_quantum_includes_exponent():
    assert one("1.5e-3").quantum == Decimal("1e-4")
    assert one("0.25").quantum == Decimal("0.01")
    assert one("12").quantum == Decimal("1")


@pytest.mark.parametrize("text,value", [
    ("-0.3", Decimal("-0.3")),
    ("−0.3", Decimal("-0.3")),
    ("+2", Decimal("2")),
    ("p=-0.3", Decimal("-0.3")),
    ("(-4)", Decimal("-4")),
    ("<-1", Decimal("-1")),
])
def test_signs(text, value):
    assert one(text).value == value


def test_range_hyphen_is_not_a_sign():
    assert [t.value for t in extract_numbers("10-20 samples")] == [Decimal(10), Decimal(20)]


def test_plus_minus_links_uncertainty():
    toks = extract_numbers("effect 3.2 ± 0.4 and 1.0 +/- 0.25 and 5 \\pm 1")
    assert [(t.text, t.role) for t in toks] == [
        ("3.2", "value"), ("0.4", "uncertainty"), ("1.0", "value"), ("0.25", "uncertainty"),
        ("5", "value"), ("1", "uncertainty")]
    assert toks[0].uncertainty is toks[1]
    assert toks[2].uncertainty.value == Decimal("0.25")


@pytest.mark.parametrize("text", [
    "F1", "e595.3", "[e595.3]", "v0.1", "x2", "COVID-19", "Type-2", "3f9a", "21d2b98599dc",
    "1st", "2nd", "3rd", "4th", "2026-11-17", "obs_12",
])
def test_identifiers_dates_ordinals_skipped(text):
    assert extract_numbers(text) == []


def test_units_may_follow():
    assert [t.value for t in extract_numbers("50ms and 3 kg, 2x faster")] == [
        Decimal(50), Decimal(3), Decimal(2)]


def test_sentence_punctuation_not_absorbed():
    assert vals("was 0.25. Then 1,234, then 7.") == [
        ("0.25", Decimal("0.25"), 2, "ok"), ("1,234", Decimal("1234"), 0, "ok"),
        ("7", Decimal("7"), 0, "ok")]


def test_en_thousands_grouping():
    assert one("1,234.5").value == Decimal("1234.5")
    assert one("12,345,678").value == Decimal("12345678")


@pytest.mark.parametrize("text", ["1.234,5", "1,2", "12,34", "1,2345", "1.234.567", "0.1.0",
                                  "1,23,456"])
def test_ambiguous_separators_fail_closed(text):
    t = one(text)
    assert t.status == "ambiguous" and t.value is None and not t.ok
    assert not agrees_at_printed_precision(t, 1)


def test_strict_convention_refuses_any_comma():
    assert one("1,234", convention="strict").status == "ambiguous"
    assert one("1234.5", convention="strict").value == Decimal("1234.5")
    with pytest.raises(ValueError):
        extract_numbers("1", convention="de")


def test_list_with_spaces_is_three_numbers():
    assert [t.value for t in extract_numbers("values 1, 2, 3")] == [1, 2, 3]


def test_latex_table_row():
    row = r"LLM & 24.0\% & 39.3\% & 46.7\% \\"
    assert [(t.value, t.percent) for t in extract_numbers(row)] == [
        (Decimal("24.0"), True), (Decimal("39.3"), True), (Decimal("46.7"), True)]


@pytest.mark.parametrize("printed,value,ok", [
    ("0.24", 0.2381, True),
    ("0.24", 0.2449, True),
    ("0.24", 0.2349, False),
    ("0.24", "0.245", True),     # half-even (half-up gives 0.25)
    ("0.24", "0.235", True),     # half-up and half-even
    ("0.25", "0.245", True),     # half-up
    ("24.0", 23.98, True),
    ("24.0", 23.9, False),
    ("1.5e-3", 0.00151, True),
    ("1.5e-3", 0.00156, False),
    ("100", 99.6, True),
    ("100", 99.4, False),
])
def test_agrees_at_printed_precision(printed, value, ok):
    assert agrees_at_printed_precision(one(printed), value) is ok


def test_agrees_refuses_non_finite():
    assert not agrees_at_printed_precision(one("1.0"), float("nan"))
    assert not agrees_at_printed_precision(one("1.0"), "abc")


@pytest.mark.parametrize("printed,value", [
    ("0.5", "1e400"),            # far outside the default precision: quantize would raise
    ("0.5", "1e999999"),
    ("0.5", "-1e999999"),
    ("1", "1e-999999999"),       # below the default exponent range
    ("1.5e-3", "9" * 60),
    ("1", "Infinity"),
])
def test_agrees_huge_values_do_not_raise(printed, value):
    # decimal.InvalidOperation (or any decimal signal) is not agreeing, never an exception
    assert agrees_at_printed_precision(one(printed), Decimal(value)) is False
    assert agrees_at_printed_precision(one(printed), value) is False


def test_agrees_long_printed_numbers_compare_exactly():
    big = "1" + "0" * 30                        # 31 digits, beyond the default 28
    assert agrees_at_printed_precision(one(big), Decimal(big))
    assert agrees_at_printed_precision(one(big), Decimal(big + ".4"))
    assert not agrees_at_printed_precision(one(big), Decimal(big + ".6"))
    assert not agrees_at_printed_precision(one(big), Decimal(big[:-1] + "1"))
    assert agrees_at_printed_precision(one("1.5e300"), Decimal("1.54e300"))
    assert not agrees_at_printed_precision(one("1.5e300"), Decimal("1.56e300"))


def test_to_dict_is_json_ready():
    d = one("3.2 ± 0.4".split(" ±")[0]).to_dict()
    assert d["value"] == "3.2" and d["decimals"] == 1
    d = extract_numbers("3.2 ± 0.4")[0].to_dict()
    assert d["uncertainty"]["value"] == "0.4"


def test_deterministic_and_ordered():
    text = "a 1, b 2.50%, c 3e2, d -4, e 1,234.5, f 1.234,5"
    a = extract_numbers(text)
    b = extract_numbers(text)
    assert a == b
    assert [t.start for t in a] == sorted(t.start for t in a)
