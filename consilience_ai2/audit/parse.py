"""Lexical parsers for the audit: p values, test statistics, effect sizes, sample sizes and
claim words. Every pattern is a fixed regular expression listed here; nothing is learned.

All functions return spans ``(start, end)`` into the text they were given, so a check can
cite exactly what it read. They are deliberately literal: they catch wording, not intent,
and docs/audit.md lists what they miss.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A number as printed in output (permissive; claims use core.numbers instead).
NUM = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?"
_NUM_RX = re.compile(NUM)

# p values: "p = 0.03", "p<0.001", "p-value: 0.2", "pvalue=1e-4", JSON "p_value": 0.0
_P_RX = re.compile(
    r"(?<![A-Za-z0-9_])[pP](?:[\s_-]?val(?:ue)?s?)?\"?\s*(?P<op><=|>=|==|=|:|<|>|≤|≥)\s*"
    r"(?P<num>" + NUM + r")"
)

# Test statistics printed in output (names, symbols and the common scipy result reprs).
_TEST_RX = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"t\s*\(\s*\d+(?:\.\d+)?\s*\)\s*=|t[-_ ]?stat(?:istic)?|t\s*=\s*" + NUM + r"|"
    r"z[-_ ]?(?:stat(?:istic)?|score)?\s*=\s*" + NUM + r"|"
    r"chi[-_ ]?(?:2|sq(?:uare)?d?)|χ²|χ2|"
    r"F\s*\(\s*\d+\s*,\s*\d+\s*\)\s*=|f[-_ ]?stat(?:istic)?|"
    r"U\s*=\s*" + NUM + r"|mann[-_ ]?whitney|wilcoxon|kruskal|"
    r"ttest|t-test|welch|anova|f_oneway|"
    r"pearsonr|spearmanr|kendalltau|fisher_exact|binom(?:ial)?[_ ]?test|"
    r"ks_2samp|kolmogorov|permutation[_ ]test|bootstrap|"
    r"statistic\s*[=:]|"
    r"[pP](?:[\s_-]?val(?:ue)?s?)?\"?\s*(?:<=|>=|==|=|:|<|>|≤|≥)\s*" + NUM +
    r")",
    re.IGNORECASE,
)

# Effect sizes: named statistics, symbols, or an explicit difference/improvement number.
_EFFECT_RX = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"cohen'?s?\s*d|hedges'?\s*g|effect[\s_-]?size|odds[\s_-]?ratio|hazard[\s_-]?ratio|"
    r"risk[\s_-]?ratio|relative[\s_-]?risk|cram[eé]r'?s?\s*v|eta[\s_-]?squared|η²|η2|"
    r"r[\s_-]?squared|r²|r\^2|auc|auroc|roc[\s_-]?auc|"
    r"(?:pearson|spearman|kendall)(?:'s)?\s*(?:r|rho|ρ|tau|τ|correlation)|"
    r"correlation(?:\s+coefficient)?\s*(?:of|=|:|was|is)|"
    r"(?:r|rho|ρ|τ|tau|d|g|β|beta|or|hr|coef(?:ficient)?|slope)\s*=\s*[-+]?\.?\d|"
    r"(?:mean|average|absolute|relative)?\s*(?:difference|improvement|increase|decrease|gain|"
    r"reduction|drop)\s+(?:of|was|=|:)\s*[-+]?\.?\d"
    r")",
    re.IGNORECASE,
)

# Claim words.
SIGNIFICANCE_RX = re.compile(r"\b(?:statistically\s+)?significan(?:t|tly|ce)\b", re.IGNORECASE)
SURPRISE_RX = re.compile(r"\bsurpris(?:ing|ingly|e)\b", re.IGNORECASE)
NULL_CLAIM_RX = re.compile(
    r"\b(?:no|not|n't|did\s+not|does\s+not|do\s+not|without|fail(?:ed|s)?\s+to|failed)\s+"
    r"(?:\w+\s+){0,3}?(?:statistically\s+)?(?:significan\w*|improv\w*|outperform\w*|differ\w*|"
    r"reach\w*\s+(?:statistical\s+)?significance|effect|association|correlat\w*)",
    re.IGNORECASE,
)
EFFECT_CLAIM_RX = re.compile(
    r"\b(?:significan(?:t|tly|ce)|outperform(?:s|ed|ing)?|improv(?:e|es|ed|ement|ements)|"
    r"better|worse|higher|lower|increase[sd]?|decrease[sd]?|correlat(?:es|ed|ion)|"
    r"associated|effects?|differs?|differences?|exceed(?:s|ed)?)\b",
    re.IGNORECASE,
)

# Sample sizes.
N_UNITS = (
    "episodes|episode|games|samples|trials|runs|instances|examples|items|tasks|participants|"
    "subjects|patients|respondents|observations|rows|records|predictions|decisions|scenarios|"
    "targets|values|questions|problems|pairs|documents|sentences|images|cases|households|individuals|"
    "people|users|seeds|environments|worlds|games|stories|datapoints|data\\s+points|"
    "test\\s+cases|evaluations|trajectories|dialogues|conversations|queries"
)
_N_EQ_RX = re.compile(r"(?<![A-Za-z0-9_])[nN]\s*(?:=|:)\s*(?P<num>\d[\d,]*)(?![\d.])")
_N_UNIT_RX = re.compile(
    r"(?<![\w.,])(?P<num>\d[\d,]*)(?![\d.])\s+(?:(?:total|random|distinct|unique|separate|"
    r"independent|different|test|training|evaluation|held[- ]out|valid|completed|"
    r"[a-z]+-?[a-z]*)\s+){0,2}(?P<unit>" + N_UNITS + r")\b",
    re.IGNORECASE,
)
_N_BOUND_BEFORE = re.compile(
    r"(?:over|more\s+than|fewer\s+than|less\s+than|at\s+least|at\s+most|up\s+to|about|"
    r"approximately|around|roughly|nearly|almost|~|≈|>|<|≥|≤)\s*$",
    re.IGNORECASE,
)
_N_NOT_SAMPLE = re.compile(r"bootstrap|resampl|permut|iteration|\bsteps?\b|epoch",
                           re.IGNORECASE)
N_UNIT_MIN = 5  # "<k> <unit>" with k below this is a design setting, not a sample size
N_KEY_EXCLUDE_RX = re.compile(r"resampl|bootstrap|permut|iter|step|seed|epoch|token|cost|time",
                              re.IGNORECASE)
_SHAPE_RX = re.compile(r"shape\s*[:=]?\s*\(\s*(?P<num>\d+)\s*,")
_LEN_RX = re.compile(r"len\([^)]*\)\s*(?:=|:|is)\s*(?P<num>\d+)")

# JSON keys whose integer values are sample sizes (CodeScientist's bootstrap helper prints
# dataset_size; generated code uses num_*/n_*).
N_KEY_RX = re.compile(
    r"^(?:n|num|count|size|n_samples|sample_size|dataset_size|num_[a-z_]+|n_[a-z_]+|"
    r"[a-z_]*_(?:count|size)|total_[a-z_]+)$",
    re.IGNORECASE,
)
P_KEY_RX = re.compile(r"^p(?:[_-]?val(?:ue)?s?)?$|^p_[a-z_]+$|^[a-z_]+_p(?:_?value)?$",
                      re.IGNORECASE)
TEST_KEY_RX = re.compile(
    r"^(?:t|z|u|f|w|h|chi2|chi_square|statistic|t_stat(?:istic)?|z_stat|u_stat|f_stat|"
    r"test_statistic|num_resamples)$", re.IGNORECASE)
EFFECT_KEY_RX = re.compile(
    r"^(?:cohens?_d|d|hedges_g|effect_size|odds_ratio|or|r|rho|r_squared|r2|auc|eta_sq(?:uared)?|"
    r"cramers_v|correlation|corr|pearson_r|spearman_r|spearman_rho|beta|coef|slope|"
    r"mean_difference|difference|diff|improvement)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PValue:
    value: float
    bound: str      # "=" exact, "<" upper bound (value is the bound), ">" lower bound
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class NMention:
    value: int
    unit: str | None
    start: int
    end: int
    text: str
    bounded: bool   # "over 600", "up to 25": not an exact n


def _to_float(s: str) -> float | None:
    try:
        v = float(s)
    except ValueError:
        return None
    return v


def find_pvalues(text: str) -> list[PValue]:
    """Every p value written in ``text`` with 0 <= p <= 1.

    "p < 0.001" is an upper bound and is kept as 0.001 (conservative for BH). A printed
    exact zero ("p = 0.0", what a resampling test prints when no resample exceeds the
    observed statistic) is kept as 0."""
    out: list[PValue] = []
    for m in _P_RX.finditer(text):
        v = _to_float(m.group("num"))
        if v is None or not (0.0 <= v <= 1.0):
            continue
        op = m.group("op")
        bound = "<" if op in ("<", "<=", "≤") else (">" if op in (">", ">=", "≥") else "=")
        out.append(PValue(v, bound, m.start(), m.end(), m.group(0)))
    return out


def find_tests(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _TEST_RX.finditer(text)]


def find_effect_sizes(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0).strip()) for m in _EFFECT_RX.finditer(text)]


def _int(s: str) -> int | None:
    s = s.replace(",", "")
    if not s.isdigit():
        return None
    return int(s)


def find_n(text: str) -> list[NMention]:
    """Sample sizes written as ``n = 50``, ``N: 50`` or ``50 <unit>`` (unit list above)."""
    out: list[NMention] = []
    seen: set[tuple[int, int]] = set()
    for rx, has_unit in ((_N_EQ_RX, False), (_N_UNIT_RX, True), (_SHAPE_RX, False),
                         (_LEN_RX, False)):
        for m in rx.finditer(text):
            v = _int(m.group("num"))
            if v is None:
                continue
            key = (m.start("num"), m.end("num"))
            if key in seen:
                continue
            seen.add(key)
            before = text[max(0, m.start() - 20):m.start()]
            around = text[max(0, m.start() - 40):m.end() + 15]
            if _N_NOT_SAMPLE.search(around):
                continue  # resamples, permutations, iterations or steps are not n
            bounded = bool(_N_BOUND_BEFORE.search(before))
            unit = m.group("unit").lower() if has_unit else None
            if has_unit and v < N_UNIT_MIN:
                continue  # "2 distractor items", "3 conditions": design settings, not n
            out.append(NMention(v, unit, m.start(), m.end(), m.group(0), bounded))
    out.sort(key=lambda x: (x.start, x.end))
    return out


def find_numbers_fast(text: str) -> list[str]:
    """Every number-like token in output text (permissive; used for evidence only)."""
    return _NUM_RX.findall(text)


def line_of(text: str, offset: int) -> int:
    """1-based line number of ``offset`` in ``text``."""
    return text.count("\n", 0, offset) + 1
