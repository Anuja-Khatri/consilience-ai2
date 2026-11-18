"""The checks A1-A7 and R1-R5, one function each, plus the U1 "nothing to check" refusal.

Each check reads a ``Node`` (and, for A5, the whole ``Run``) and returns ``Check``
records. A check that passes returns an ``info`` record with a receipt; a check that
cannot apply returns nothing and is listed in the node's ``not_applicable``.

Rules version ``audit-rules-2`` (v0.2). Severities are fixed by what a reviewer would do
with the finding:

- ``error``, the things a reviewer rejects a result for: a number in the write-up that is
  in no output, code or plan (A1); a column the code reads that the dataset does not have
  (A3, code); "significant" with no test printed (A4); a random-only comparator (R1);
  reruns that mostly fail to support the result (R2, refutes at least as many as
  supports); a hard-coded result (R4); a component that reaches no output (R5); and U1.
- ``warning``, problems a reviewer would ask about: A1 numbers that agree only at a
  coarser precision than the write-up prints, or that may be printed only in a saved
  figure; A2; A3 (a hypothesis mention); A5; A6; R2 with a supporting majority; R3.
- ``info`` notes on reporting conventions, which never flag: A7 (no effect size), with
  ``details.status = "not_reported"``.

The verdict (``verdict_level``) is explicit: ``refuse`` when nothing can be checked (U1),
``flag(error)`` on any other error, ``flag(warning)`` on warnings only, else ``pass``.
``verdict`` keeps the three-way value (``pass``, ``flag``, ``refuse``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from consilience_ai2.audit import stats
from consilience_ai2.audit.codeanalysis import CodeFacts, analyse
from consilience_ai2.audit.model import CLAIM, CODE, CONTEXT, EVIDENCE, Node, Run, TextField
from consilience_ai2.audit.parse import (
    EFFECT_CLAIM_RX,
    EFFECT_KEY_RX,
    N_KEY_EXCLUDE_RX,
    N_KEY_RX,
    NULL_CLAIM_RX,
    P_KEY_RX,
    SIGNIFICANCE_RX,
    SURPRISE_RX,
    TEST_KEY_RX,
    find_effect_sizes,
    find_n,
    find_numbers_fast,
    find_pvalues,
    find_tests,
    line_of,
)
from consilience_ai2.core.numbers import (
    NumberToken,
    agrees_at_printed_precision,
    extract_numbers,
)

ERROR, WARNING, INFO = "error", "warning", "info"
CODES = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "R1", "R2", "R3", "R4", "R5")
REFUSE_CODES = ("U1",)
COARSER_MIN_SIG = 3  # A1 v0.2: significant digits a printed number needs to support a
                     # claim that shows one more digit than it
NOT_REPORTED = "not_reported"  # details.status of an info note on a reporting convention
VERDICT_LEVELS = ("pass", "flag(warning)", "flag(error)", "refuse")
_SCALES = (Decimal(1), Decimal(100), Decimal("0.01"))
_BOUND_BEFORE = re.compile(
    r"(?:<|>|≤|≥|<=|>=|\\leq?|\\geq?|\\lt|\\gt|less\s+than|more\s+than|greater\s+than|"
    r"fewer\s+than|at\s+least|at\s+most|up\s+to|over|under|below|above|exceed(?:s|ing)?|"
    r"beyond)\s*\$?\s*$",
    re.IGNORECASE,
)


@dataclass
class Check:
    code: str
    severity: str
    message: str
    field: str | None = None
    span: str | None = None
    file: str | None = None
    line: int | None = None
    offset: int | None = None
    end: int | None = None
    sha256: str | None = None
    source: str | None = None
    details: dict[str, Any] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {"code": self.code, "severity": self.severity, "message": self.message,
             "field": self.field, "span": self.span, "file": self.file, "line": self.line,
             "offset": self.offset, "end": self.end, "sha256": self.sha256,
             "source": self.source}
        if self.details:
            d["details"] = self.details
        return d


def _at(code: str, sev: str, msg: str, f: TextField | None, start: int | None = None,
        end: int | None = None, **details: Any) -> Check:
    if f is None:
        return Check(code, sev, msg, details=details)
    line = line_of(f.text, start) if start is not None else None
    span = f.text[start:end] if start is not None and end is not None else None
    return Check(code, sev, msg, field=f.name, span=span, file=f.file, line=line,
                 offset=start, end=end, sha256=f.file_sha256, source=f.source,
                 details=details)


def _at_code(code: str, sev: str, msg: str, f: TextField, line: int | None, **details: Any
             ) -> Check:
    span = None
    if line is not None:
        lines = f.text.splitlines()
        if 1 <= line <= len(lines):
            span = lines[line - 1].strip()[:200]
    return Check(code, sev, msg, field=f.name, span=span, file=f.file, line=line,
                 sha256=f.file_sha256, source=f.source, details=details)


# --------------------------------------------------------------------------- context


class NumberIndex:
    """Absolute values of every number in a body of text, at each printed precision.

    ``printed`` keeps each number printed with at least ``COARSER_MIN_SIG`` significant
    digits, with the precision it was printed at (its decimal exponent; x100 drops two
    decimal places, /100 adds two), for the v0.2 precision-mismatch test (``coarser``).
    The floor keeps that test as specific as the exact test is for a three-digit claim: a
    looser match against long logs full of numbers would support almost anything."""

    def __init__(self, tokens: list[str]):
        vals: set[Decimal] = set()
        printed: set[tuple[Decimal, int]] = set()
        for t in tokens:
            try:
                d = Decimal(t)
            except InvalidOperation:
                continue
            if d.is_finite():
                d = abs(d)
                tup = d.as_tuple()
                exp = tup.exponent
                for s in _SCALES:
                    vals.add(d * s)
                if isinstance(exp, int) and len(tup.digits) >= COARSER_MIN_SIG and \
                        any(tup.digits):
                    for s, shift in ((Decimal(1), 0), (Decimal(100), 2),
                                     (Decimal("0.01"), -2)):
                        e = exp + shift
                        try:
                            printed.add(((d * s).quantize(Decimal(1).scaleb(e)), e))
                        except InvalidOperation:
                            continue
        self.values = vals
        self.printed = printed
        self._by_quantum: dict[Decimal, set[Decimal]] = {}

    def _quantised(self, q: Decimal) -> set[Decimal]:
        got = self._by_quantum.get(q)
        if got is None:
            got = set()
            for v in self.values:
                for r in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                    try:
                        got.add(v.quantize(q, rounding=r))
                    except InvalidOperation:
                        continue
            self._by_quantum[q] = got
        return got

    def supports(self, tok: NumberToken) -> bool:
        if tok.value is None:
            return False
        q = tok.quantum
        assert q is not None
        try:
            target = abs(tok.value).quantize(q)
        except InvalidOperation:
            return False
        return target in self._quantised(q)

    def coarser(self, tok: NumberToken, places: int = 1) -> bool:
        """True when ``tok`` agrees with a number printed (with at least
        ``COARSER_MIN_SIG`` significant digits) with one fewer decimal place than ``tok``
        shows: the write-up gives one more digit than the run printed."""
        if tok.value is None or tok.quantum is None:
            return False
        ce = tok.quantum.as_tuple().exponent
        if not isinstance(ce, int):
            return False
        v = abs(tok.value)
        for e in range(ce + 1, ce + 1 + places):
            for r in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                try:
                    if (v.quantize(Decimal(1).scaleb(e), rounding=r), e) in self.printed:
                        return True
                except InvalidOperation:
                    continue
        return False


def _json_walk(obj: Any, depth: int = 0, key: str | None = None):
    """Yield (key, value, depth) for every leaf and every list (as its length)."""
    if depth > 6:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _json_walk(v, depth + 1, str(k))
    elif isinstance(obj, list):
        yield (key, ("__len__", len(obj)), depth)
        for v in obj[:2000]:
            yield from _json_walk(v, depth + 1, key)
    else:
        yield (key, obj, depth)


@dataclass
class Context:
    node: Node
    facts: CodeFacts | None
    code: TextField | None
    output_index: NumberIndex
    code_index: NumberIndex
    context_index: NumberIndex
    printed_n: dict[int, str]
    stated_n: list[tuple[TextField, Any]]
    pvalues: list[tuple[float, str, TextField | None, int | None, int | None]]
    has_test: tuple[TextField | None, int | None, int | None, str] | None
    has_effect: tuple[TextField | None, int | None, int | None, str] | None
    claims_significance: tuple[TextField, int, int] | None
    claims_null: tuple[TextField, int, int] | None
    claims_effect: tuple[TextField, int, int] | None
    n_eff: int | None
    n_eff_source: str | None


def _first(rx: re.Pattern, fields: list[TextField]) -> tuple[TextField, int, int] | None:
    for f in fields:
        for m in rx.finditer(f.text):
            if not f.masked(m.start(), m.end()):
                return f, m.start(), m.end()
    return None


def _headline_null(node: Node, claims: list[TextField]) -> tuple[TextField, int, int] | None:
    """A null claim in the headline (a report's abstract when it has one, else any claim
    field)."""
    head = node.meta.get("headline")
    if head:
        name, s, e = head
        f = node.get(name)
        if f is not None:
            m = NULL_CLAIM_RX.search(f.text, s, e)
            return (f, m.start(), m.end()) if m else None
    return _first(NULL_CLAIM_RX, claims)


def build_context(node: Node) -> Context:
    code = node.get("code")
    facts = analyse(code.text) if code is not None and code.text.strip() else None
    ev = node.of_kind(EVIDENCE)
    out_tokens: list[str] = []
    for f in ev:
        out_tokens.extend(find_numbers_fast(f.text))
    code_tokens = [lit.value for lit in facts.literals] if facts and facts.ok else []
    if code is not None and (facts is None or not facts.ok):
        code_tokens = find_numbers_fast(code.text)
    ctx_tokens: list[str] = []
    for f in node.of_kind(CONTEXT):
        ctx_tokens.extend(find_numbers_fast(f.text))

    printed_n: dict[int, str] = {}
    for f in ev:
        for m in find_n(f.text):
            if not m.bounded and m.value >= 2:
                printed_n.setdefault(m.value, f"{f.name}: {m.text}")
    pvals: list[tuple[float, str, TextField | None, int | None, int | None]] = []
    test_hit = None
    effect_hit = None
    for f in ev:
        for p in find_pvalues(f.text):
            pvals.append((p.value, p.bound, f, p.start, p.end))
        if test_hit is None:
            t = find_tests(f.text)
            if t:
                test_hit = (f, t[0][0], t[0][1], t[0][2])
        if effect_hit is None:
            e = find_effect_sizes(f.text)
            if e:
                effect_hit = (f, e[0][0], e[0][1], e[0][2])
    if node.results is not None:
        res_f = node.get("results")
        for k, v, _d in _json_walk(node.results, key="<root>"):
            if k is None:
                continue
            if isinstance(v, tuple) and v[0] == "__len__":
                if v[1] >= 2 and not N_KEY_EXCLUDE_RX.search(k):
                    printed_n.setdefault(v[1], f"results: len({k})")
                continue
            if isinstance(v, bool) or not isinstance(v, int | float):
                continue
            if N_KEY_RX.match(k) and not N_KEY_EXCLUDE_RX.search(k) and isinstance(v, int) \
                    and v >= 2:
                printed_n.setdefault(v, f"results: {k}={v}")
            if P_KEY_RX.match(k) and 0.0 <= float(v) <= 1.0:
                pvals.append((float(v), "=", res_f, None, None))
                if test_hit is None:
                    test_hit = (res_f, None, None, f"results key {k}")
            if TEST_KEY_RX.match(k) and test_hit is None:
                test_hit = (res_f, None, None, f"results key {k}")
            if EFFECT_KEY_RX.match(k) and effect_hit is None:
                effect_hit = (res_f, None, None, f"results key {k}")
    claims = node.of_kind(CLAIM)
    if effect_hit is None:
        for f in claims:
            e = [x for x in find_effect_sizes(f.text) if not f.masked(x[0], x[1])]
            if e:
                effect_hit = (f, e[0][0], e[0][1], e[0][2])
                break
    stated: list[tuple[TextField, Any]] = []
    for f in claims + node.of_kind(CONTEXT):
        for m in find_n(f.text):
            if not m.bounded and m.value >= 2 and not f.masked(m.start, m.end):
                stated.append((f, m))
    n_eff, n_src = None, None
    if printed_n:
        n_eff = max(printed_n)
        n_src = "printed: " + printed_n[n_eff]
    elif stated:
        f, m = max(stated, key=lambda x: x[1].value)
        n_eff, n_src = m.value, f"stated in {f.name}: {m.text}"
    elif facts and facts.ok and facts.n_constants:
        n_eff = max(facts.n_constants)
        n_src = f"code constant (line {facts.n_constants[n_eff]})"
    return Context(
        node=node, facts=facts, code=code,
        output_index=NumberIndex(out_tokens), code_index=NumberIndex(code_tokens),
        context_index=NumberIndex(ctx_tokens), printed_n=printed_n, stated_n=stated,
        pvalues=pvals, has_test=test_hit, has_effect=effect_hit,
        claims_significance=_first(SIGNIFICANCE_RX, claims) or _first(SURPRISE_RX, claims),
        claims_null=_headline_null(node, claims),
        claims_effect=_first(EFFECT_CLAIM_RX, claims),
        n_eff=n_eff, n_eff_source=n_src,
    )


def _claim_numbers(f: TextField) -> tuple[list[NumberToken], int, int]:
    """Result-like numbers in a claim field: decimals and percentages, not bounds.
    Returns (tokens, bounds skipped, ambiguous skipped)."""
    toks: list[NumberToken] = []
    bounds = ambiguous = 0
    for t in extract_numbers(f.text):
        if f.masked(t.start, t.end) or t.role != "value":
            continue
        if t.status != "ok":
            ambiguous += 1
            continue
        if t.decimals == 0 and not t.percent:
            continue
        if _BOUND_BEFORE.search(f.text[max(0, t.start - 24):t.start]):
            bounds += 1
            continue
        toks.append(t)
    return toks, bounds, ambiguous


# --------------------------------------------------------------------------- checks


_CHANGE_RX = re.compile(
    r"\b(?:increase[sd]?|decrease[sd]?|reduction|reduced|improve(?:ment|d|s)?|gains?|drops?|"
    r"declines?|rises?|higher|lower|more|less|fewer|faster|slower|larger|smaller|better|worse|"
    r"differences?|ratio|times|fold|relative)\b", re.IGNORECASE)
# A sentence for A1: a full stop inside a number ("29.8") or an abbreviation does not end it.
_SENT_SPAN = re.compile(r"(?:[^.!?\n]|[.!?](?=\S))+(?:[.!?]|$)")


def _sentence(text: str, pos: int) -> tuple[int, int]:
    for m in _SENT_SPAN.finditer(text):
        if m.start() <= pos < m.end():
            return m.start(), m.end()
    return 0, len(text)


def _derived(c: Context, f: TextField, t: NumberToken) -> str | None:
    """v0.2: a relative change, ratio or difference of two other numbers of the same
    sentence, each of which is itself printed (or in the code or plan), and worded as a
    change ("a 76% increase"). Returns how it was derived, or None."""
    s, e = _sentence(f.text, t.start)
    near = f.text[max(s, t.start - 40):min(e, t.end + 40)]
    if not _CHANGE_RX.search(near):
        return None
    ops = []
    for o in extract_numbers(f.text[s:e]):
        if o.status != "ok" or o.value is None or o.role != "value" or o.value == 0:
            continue
        if s + o.start == t.start:
            continue
        if c.output_index.supports(o) or c.code_index.supports(o) or \
                c.context_index.supports(o):
            ops.append(o)
    for a in ops:
        for b in ops:
            if a is b:
                continue
            x, y = abs(a.value), abs(b.value)  # type: ignore[arg-type]
            cands = (("ratio", x / y), ("relative change", abs(x / y - 1)),
                     ("difference", abs(x - y)))
            for name, v in cands:
                if agrees_at_printed_precision(t, v) or \
                        (t.percent and agrees_at_printed_precision(t, v * 100)):
                    return f"{name} of {a.text} and {b.text}"
    return None


def check_a1(c: Context) -> list[Check]:
    """v0.2 tiers for a decimal or percentage in a claim: printed, in the code or plan, or
    derived (info); printed only at a coarser precision, or possibly printed only in a saved
    figure (warning); in no output at all (error)."""
    out: list[Check] = []
    claims = c.node.of_kind(CLAIM)
    if not claims or not c.node.of_kind(EVIDENCE):
        return out
    total = supported_out = supported_code = supported_ctx = bounds = ambiguous = 0
    derived: list[str] = []
    figs = c.facts.figure_text_lines if c.facts is not None and c.facts.ok else []
    for f in claims:
        toks, b, a = _claim_numbers(f)
        bounds += b
        ambiguous += a
        for t in toks:
            total += 1
            if c.output_index.supports(t):
                supported_out += 1
            elif c.code_index.supports(t):
                supported_code += 1
            elif c.context_index.supports(t):
                supported_ctx += 1
            elif (how := _derived(c, f, t)) is not None:
                derived.append(f"{t.text}: {how}")
            elif c.output_index.coarser(t):
                out.append(_at("A1", WARNING,
                               f"{t.text} agrees with the output only at a coarser precision: "
                               "the write-up gives more digits than the run printed", f,
                               t.start, t.end, value=t.text, tier="coarser_precision"))
            elif figs:
                out.append(_at("A1", WARNING,
                               f"{t.text} is in no text output, code or plan; the code writes "
                               f"formatted values into saved figures (lines {figs[:6]}), which "
                               "the audit cannot read", f, t.start, t.end, value=t.text,
                               tier="figure_only", figure_lines=figs[:20]))
            else:
                out.append(_at("A1", ERROR,
                               f"{t.text} is not printed in the run's output or code at the "
                               "printed precision", f, t.start, t.end, value=t.text,
                               tier="absent"))
    if not out and total:
        f = claims[0]
        out.append(_at("A1", INFO, f"all {total} result numbers found in output, code or plan"
                       f"{f' ({len(derived)} derived from them)' if derived else ''}", f,
                       0, 0, checked=total, from_output=supported_out, from_code=supported_code,
                       from_plan=supported_ctx, derived=len(derived), derived_from=derived[:20],
                       bounds_skipped=bounds, ambiguous_skipped=ambiguous))
    for ch in out:
        ch.details.setdefault("checked", total)
    return out


def check_a2(c: Context) -> list[Check]:
    """Stated n must be printed or be an n constant in the code. A stated n that is
    neither (the plan says 2000, the code and output say 20) is flagged."""
    out: list[Check] = []
    if not c.stated_n:
        return out
    code_n = c.facts.n_constants if c.facts and c.facts.ok else {}
    for f, m in c.stated_n:
        if m.value in c.printed_n:
            out.append(_at("A2", INFO, f"stated n {m.value} is printed "
                           f"({c.printed_n[m.value]})", f, m.start, m.end, n=m.value))
        elif m.value in code_n:
            out.append(_at("A2", INFO, f"stated n {m.value} matches a code constant "
                           f"(line {code_n[m.value]}) but is not printed", f, m.start, m.end,
                           n=m.value, code_line=code_n[m.value]))
        else:
            out.append(_at("A2", WARNING,
                           f"stated n {m.value} is neither printed in the output nor an n "
                           f"constant in the code (printed: {sorted(c.printed_n)[:8]}; code: "
                           f"{sorted(code_n)[:8]})", f, m.start, m.end, n=m.value,
                           printed_n=sorted(c.printed_n)[:20], code_n=sorted(code_n)[:20]))
    return out


_SNAKE = re.compile(r"`([^`\n]{1,60})`|\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")


def check_a3(c: Context) -> list[Check]:
    out: list[Check] = []
    cols = c.node.columns
    if cols is None:
        return out
    low = {x.strip().lower() for x in cols}

    def present(name: str) -> bool:
        if name in cols or name.strip().lower() in low:
            return True
        if c.facts and c.facts.uses_dummies:
            return any(name.lower().startswith(x + "_") for x in low)
        return False

    checked = 0
    if c.facts is not None and c.facts.ok and c.code is not None:
        created = c.facts.columns_created
        for name, line in sorted(c.facts.columns_read.items(), key=lambda kv: (kv[1], kv[0])):
            if name in created:
                continue
            checked += 1
            if not present(name):
                out.append(_at_code("A3", ERROR, f"column {name!r} is read by the code but is "
                                    "not in the dataset metadata", c.code, line, column=name,
                                    metadata=c.node.columns_source))
    hyp = c.node.get("hypothesis")
    if hyp is not None:
        for m in _SNAKE.finditer(hyp.text):
            name = m.group(1) or m.group(2)
            checked += 1
            if not present(name) and not (c.facts and name in c.facts.columns_created):
                out.append(_at("A3", WARNING, f"{name!r} in the hypothesis is not a dataset "
                               "column", hyp, m.start(), m.end(), column=name,
                               metadata=c.node.columns_source))
    if not out and checked:
        out.append(_at("A3", INFO, f"{checked} column names found in the metadata",
                       c.code or hyp, None, None, checked=checked,
                       metadata=c.node.columns_source))
    return out


def _is_surprising(c: Context) -> bool:
    if c.node.surprising is not None:
        return bool(c.node.surprising)
    return c.claims_significance is not None


def check_a4(c: Context) -> list[Check]:
    claim = c.claims_significance
    if not c.node.surprising and claim is None:
        return []
    if c.has_test is not None:
        f, s, e, what = c.has_test
        return [_at("A4", INFO, f"a test statistic or p value is printed ({what.strip()[:40]})",
                    f, s, e)]
    if claim is not None:
        f, s, e = claim
        return [_at("A4", ERROR, f"{f.text[s:e]!r} claimed with no test statistic or p value "
                    "printed in the output", f, s, e)]
    return [Check("A4", ERROR, "node is marked surprising but no test statistic or p value "
                  "is printed in the output")]


def check_a5(run: Run, ctxs: dict[str, Context]) -> tuple[dict[str, list[Check]],
                                                             dict[str, float | None], dict]:
    """BH across every p value parsed from the run (distinct values per node)."""
    fam: list[tuple[str, float]] = []
    per_node: dict[str, list[float]] = {}
    for nid, c in ctxs.items():
        seen: list[float] = []
        for v, _b, _f, _s, _e in c.pvalues:
            if v not in seen:
                seen.append(v)
        per_node[nid] = seen
        fam.extend((nid, v) for v in seen)
    qs = stats.benjamini_hochberg([v for _, v in fam])
    qmin: dict[str, float | None] = {nid: None for nid in ctxs}
    for (nid, _v), q in zip(fam, qs, strict=True):
        qmin[nid] = q if qmin[nid] is None else min(qmin[nid], q)
    out: dict[str, list[Check]] = {nid: [] for nid in ctxs}
    for nid, c in ctxs.items():
        if not per_node[nid]:
            continue
        q = qmin[nid]
        assert q is not None
        first = next(((f, s, e) for v, b, f, s, e in c.pvalues if f is not None), None)
        f, s, e = first if first else (None, None, None)
        p = min(per_node[nid])
        if _is_surprising(c) and not _is_null(c) and q > stats.Q_THRESHOLD:
            out[nid].append(_at("A5", WARNING,
                                f"surprising node, but BH q = {q:.3g} > {stats.Q_THRESHOLD} "
                                f"across {len(fam)} p values in the run", f, s, e,
                                q=q, min_p=p, family_size=len(fam)))
        else:
            out[nid].append(_at("A5", INFO, f"BH q = {q:.3g} (min p = {p:.3g}, family "
                                f"{len(fam)})", f, s, e, q=q, min_p=p, family_size=len(fam)))
    n_checkable = sum(1 for c in ctxs.values() if c.node.uncheckable is None)
    n_with = sum(1 for nid in ctxs if per_node[nid])
    coverage = {"nodes_with_pvalue": n_with, "nodes_checkable": n_checkable,
                "pvalues": len(fam),
                "rate": (n_with / n_checkable) if n_checkable else None}
    return out, qmin, coverage


def _is_null(c: Context) -> bool:
    n = c.node
    if n.prior_mean is not None and n.posterior_mean is not None and n.surprising:
        sig = any(v < stats.ALPHA for v, b, *_ in c.pvalues)
        return n.posterior_mean < n.prior_mean and not sig
    # without beliefs (CodeScientist), every reported experiment is a candidate finding
    return (n.surprising is None or bool(n.surprising)) and c.claims_null is not None


def check_a6(c: Context) -> list[Check]:
    if not _is_null(c):
        return []
    f, s, e = c.claims_null if c.claims_null else (c.node.get("analysis"), None, None)
    if c.n_eff is None:
        return [_at("A6", WARNING, "surprising null with no parseable n: the minimum "
                    "detectable effect is unknown", f, s, e)]
    d, r = stats.mde_d(c.n_eff), stats.mde_r(c.n_eff)
    det = dict(n=c.n_eff, n_source=c.n_eff_source, mde_d=round(d, 4), mde_r=round(r, 4),
               alpha=stats.ALPHA, power=stats.POWER)
    if d > stats.A6_MAX_MDE_D:
        return [_at("A6", WARNING, f"surprising null at n = {c.n_eff}: only effects of "
                    f"d >= {d:.2f} (r >= {r:.2f}) were detectable at 80% power",
                    f, s, e, **det)]
    return [_at("A6", INFO, f"surprising null at n = {c.n_eff}; minimum detectable d = "
                f"{d:.2f} (r = {r:.2f})", f, s, e, **det)]


def check_a7(c: Context) -> list[Check]:
    """A reporting convention (v0.2: info, never a flag): an effect claim without an effect
    size gets an info note with ``details.status = "not_reported"``."""
    if not (_is_surprising(c) or c.claims_effect is not None):
        return []
    if c.has_effect is not None:
        f, s, e, what = c.has_effect
        return [_at("A7", INFO, f"effect size present ({what[:40]})", f, s, e)]
    f, s, e = c.claims_effect or (None, None, None)
    return [_at("A7", INFO, "reporting convention: an effect is claimed but no effect size (d, "
                "r, OR, beta, AUC, eta squared, a stated difference) is printed or reported",
                f, s, e, status=NOT_REPORTED)]


_COMPARE_RX = re.compile(
    r"\b(?:vs\.?|versus|compared\s+(?:to|with|against)|against|outperform\w*|than|"
    r"relative\s+to|baselines?|control|over)\b", re.IGNORECASE)
_RANDOM_RX = re.compile(
    r"\brandom[- ](?:baselines?|agents?|polic(?:y|ies)|exploration|explorers?|guess(?:ing|es)?|"
    r"actions?|play(?:ers?)?|performance|walks?|choices?|predictors?|classifiers?|models?|"
    r"level|selection|strateg(?:y|ies)|controllers?)\b|"
    r"\bchance(?:[- ]level)?\b|"
    r"\b(?:than|vs\.?|versus|compared\s+(?:to|with|against)|over|against)\s+(?:a\s+|the\s+)?"
    r"random\b",
    re.IGNORECASE)
# v0.2: a random or chance comparator qualified by these words is a limiting or negative
# statement ("only slightly better than random", "no better than chance"), not a claim
# that rests on beating a random baseline.
_LIMITING_RX = re.compile(
    r"\b(?:only|barely|slightly|marginally|hardly|scarcely|no|not|n't|never|near(?:ly)?|"
    r"close\s+to|indistinguishable|comparable|similar|equivalent)\b", re.IGNORECASE)
_AT_CHANCE_RX = re.compile(r"\b(?:at|around|about|approximately)\s+(?:the\s+)?$", re.IGNORECASE)
_FUTURE_RX = re.compile(r"\b(?:future|should|could|would|need(?:s|ed)?|recommend\w*|might)\b",
                        re.IGNORECASE)
_PLAIN_BASELINE_RX = re.compile(r"\b(?:baselines?|control(?:\s+condition|\s+group)?)\b",
                                re.IGNORECASE)
_NOT_PLAIN = re.compile(r"(?:random|chance|additional|stronger|more|other|better|sophisticated|"
                        r"non-random|alternative|different|competitive|strong|simple\s+random)"
                        r"[\s-]+(?:\w+[\s-]+)?$", re.IGNORECASE)
_MULTI_ARM_RX = re.compile(
    r"\b(?:three|four|five|six|seven|eight|nine|ten|[3-9]|1\d)\s+(?:\w+\s+)?"
    r"(?:agents|conditions|approaches|methods|variants|systems|baselines|models|configurations|"
    r"arms|strategies|settings|agent\s+variants|levels)\b", re.IGNORECASE)
_COORD_RX = re.compile(r"\b([A-Za-z][\w-]+)\s+and\s+random\b|\brandom\s+(?:\w+\s+)?and\s+"
                       r"(?:a\s+|the\s+)?([A-Za-z][\w-]+)", re.IGNORECASE)
_SENT = re.compile(r"[^.!?\n]+(?:[.!?]|$)")
_STOP = {"the", "a", "an", "both", "all", "its", "their", "other", "baseline", "baselines"}


def _limiting(sent: str, start: int) -> bool:
    before = sent[max(0, start - 30):start]
    return bool(_LIMITING_RX.search(before) or _AT_CHANCE_RX.search(before))


def check_r1(c: Context) -> list[Check]:
    """R1: the only comparator named is random or chance (lexical; see docs/audit.md).
    v0.2: a random comparator in a limiting or negative statement is not counted."""
    rnd = None
    other = None
    limiting = None
    for f in c.node.of_kind(CLAIM):
        for sm in _SENT.finditer(f.text):
            sent = sm.group(0)
            if f.masked(sm.start(), sm.end()) or _FUTURE_RX.search(sent):
                continue
            if other is None:
                mm = _MULTI_ARM_RX.search(sent)
                if mm:
                    other = (f, sm.start() + mm.start(), sm.start() + mm.end())
            if not _COMPARE_RX.search(sent):
                continue
            for r in _RANDOM_RX.finditer(sent):
                span = (f, sm.start() + r.start(), sm.start() + r.end())
                if _limiting(sent, r.start()):
                    limiting = limiting or span
                elif rnd is None:
                    rnd = span
            if other is None:
                for o in _PLAIN_BASELINE_RX.finditer(sent):
                    if not _NOT_PLAIN.search(sent[max(0, o.start() - 30):o.start()]):
                        other = (f, sm.start() + o.start(), sm.start() + o.end())
                        break
            if other is None:
                for o in _COORD_RX.finditer(sent):
                    w = (o.group(1) or o.group(2) or "").lower()
                    if w and w not in _STOP:
                        other = (f, sm.start() + o.start(), sm.start() + o.end())
                        break
    if rnd is None:
        if limiting is not None:
            f, s, e = limiting
            return [_at("R1", INFO, "a random or chance comparator appears only in a limiting "
                        f"or negative statement ({f.text[s:e]!r})", f, s, e)]
        return []
    if other is not None:
        f, s, e = other
        return [_at("R1", INFO, f"a non-random comparator is named ({f.text[s:e]!r})", f, s, e)]
    f, s, e = rnd
    return [_at("R1", ERROR, "the only comparator named is random or chance", f, s, e)]


_SUPPORT = {"support", "supports", "supported", "confirm", "confirmed"}
_REFUTE = {"refute", "refutes", "refuted", "reject", "rejected", "contradict"}


def check_r2(c: Context) -> list[Check]:
    runs = c.node.reruns
    if not runs or len(runs) < 2:
        return []
    labels = [r.strip().lower() for r in runs]
    s = sum(1 for x in labels if x in _SUPPORT)
    r = sum(1 for x in labels if x in _REFUTE)
    i = len(labels) - s - r
    det = dict(support=s, refute=r, other=i, reruns=len(labels), source=c.node.rerun_source)
    if s and r:
        if r >= s:
            return [Check("R2", ERROR, f"verdict flips across {len(labels)} reruns and refutes "
                          f"are at least as many as supports ({s} support, {r} refute, {i} "
                          "other): the result does not replicate", details=det)]
        return [Check("R2", WARNING, f"verdict flips across {len(labels)} reruns, with a "
                      f"supporting majority ({s} support, {r} refute, {i} other)",
                      details=det)]
    return [Check("R2", INFO, f"no support/refute flip across {len(labels)} reruns",
                  details=det)]


def check_r3(c: Context) -> list[Check]:
    if c.claims_effect is None and c.claims_significance is None:
        return []
    if _is_null(c):
        return []  # a null is judged by A6
    f, s, e = c.claims_significance or c.claims_effect  # type: ignore[misc]
    floor = stats.R3_N_FLOOR
    if c.n_eff is None:
        return [_at("R3", INFO, "no n parsed; the sample-size floor cannot be checked", f, s, e,
                    floor=floor)]
    det = dict(n=c.n_eff, n_source=c.n_eff_source, floor=floor, effect_d=stats.R3_EFFECT_D,
               pilot_mode=c.node.pilot_mode)
    if c.n_eff < floor:
        return [_at("R3", WARNING, f"claim rests on n = {c.n_eff}, below the floor of {floor} "
                    f"per group needed to detect even a large effect (d = {stats.R3_EFFECT_D}) "
                    "at 80% power", f, s, e, **det)]
    return [_at("R3", INFO, f"n = {c.n_eff} meets the floor of {floor}", f, s, e, **det)]


def _sig_digits(v: str) -> int:
    mant = v.lstrip("+-").split("e")[0].split("E")[0]
    if "." in mant:
        return len(mant.replace(".", "").lstrip("0"))
    return len(mant.lstrip("0").rstrip("0"))


def _literal_matches(tok: NumberToken, lit: str) -> bool:
    """A reported number equals a code literal: same value at the printed precision, or a
    percentage equal to a fraction literal times 100."""
    try:
        v = Decimal(lit)
    except InvalidOperation:
        return False
    from consilience_ai2.core.numbers import agrees_at_printed_precision
    if agrees_at_printed_precision(tok, abs(v)):
        return True
    return tok.percent and agrees_at_printed_precision(tok, abs(v) * 100)


def check_r4(c: Context) -> list[Check]:
    if c.facts is None or not c.facts.ok or c.code is None:
        return []
    lits = [lit for lit in c.facts.literals if lit.on_output_path and _sig_digits(lit.value) >= 2]
    if not lits:
        return []
    out: list[Check] = []
    for f in c.node.of_kind(CLAIM):
        toks, _b, _a = _claim_numbers(f)
        for t in toks:
            for lit in lits:
                if _literal_matches(t, lit.value):
                    out.append(_at("R4", ERROR,
                                   f"{t.text} matches a literal {lit.value} written in the code "
                                   f"on the output path (line {lit.line}, {lit.context})",
                                   f, t.start, t.end, literal=lit.value, code_line=lit.line,
                                   code_file=c.code.file, code_sha256=c.code.file_sha256,
                                   context=lit.context))
                    break
    return out


def check_r5(c: Context) -> list[Check]:
    if c.facts is None or c.code is None:
        return []
    if not c.facts.ok:
        return [_at_code("R5", INFO, f"code does not parse: {c.facts.error}", c.code, None)]
    if c.facts.r5_uncheckable:
        return [_at_code("R5", INFO, f"not decidable: {c.facts.r5_uncheckable}", c.code, None)]
    out = [_at_code("R5", ERROR, f"{kind} {name!r} is used but nothing it computes reaches any "
                    "printed or saved output", c.code, line, component=name, kind=kind)
           for name, line, kind in c.facts.unused_components]
    if not out:
        out.append(_at_code("R5", INFO, f"{c.facts.components_checked} components checked: all "
                            "reach an output", c.code, None))
    return out


NODE_CHECKS = (("A1", check_a1), ("A2", check_a2), ("A3", check_a3), ("A4", check_a4),
               ("A6", check_a6), ("A7", check_a7), ("R1", check_r1), ("R2", check_r2),
               ("R3", check_r3), ("R4", check_r4), ("R5", check_r5))


def verdict_level(checks: list[Check], uncheckable: bool) -> str:
    """``refuse`` (nothing can be checked), ``flag(error)``, ``flag(warning)`` or ``pass``."""
    if uncheckable or any(ch.severity == ERROR and ch.code in REFUSE_CODES for ch in checks):
        return "refuse"
    if any(ch.severity == ERROR for ch in checks):
        return "flag(error)"
    if any(ch.severity == WARNING for ch in checks):
        return "flag(warning)"
    return "pass"


def verdict(checks: list[Check], uncheckable: bool) -> str:
    """The three-way verdict: ``pass``, ``flag`` or ``refuse``."""
    level = verdict_level(checks, uncheckable)
    return "flag" if level.startswith("flag") else level


def notes(checks: list[Check]) -> list[str]:
    """Codes of info notes on reporting conventions (``details.status == "not_reported"``)."""
    return sorted({ch.code for ch in checks
                   if ch.severity == INFO and ch.details.get("status") == NOT_REPORTED})


def has_kind(node: Node, kind: str) -> bool:
    return any(f.text.strip() for f in node.of_kind(kind))


__all__ = ["CODES", "CODE", "Check", "Context", "NODE_CHECKS", "NOT_REPORTED", "VERDICT_LEVELS",
           "build_context", "check_a5", "has_kind", "notes", "verdict", "verdict_level"]

CLAIM_KINDS_NOTE = ("claim fields (A1, A4, A6, A7, R1, R3, R4): AutoDiscovery analysis, and review "
                    "when the reviewer passed the node; a CodeScientist report (report.tex, else "
                    "the run's summary)")
EVIDENCE_NOTE = ("evidence fields (what was printed or saved): AutoDiscovery code_output; "
                 "CodeScientist stdout, log.json and results.json of the final run")
