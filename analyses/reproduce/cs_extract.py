"""Extraction rule v0.2 for CodeScientist run outputs: parsers and the primary-comparison
rule. Pure functions over bytes and parsed objects, so every rule is unit-tested without
the data (``tests/reproduce/test_cs_extract.py``). The rule is fixed in
``prereg/reproduce/cs_extraction_v0_2.md``, with the corrections of
``prereg/reproduce/cs_extraction_v0_2_deviations.md`` (``RULES`` keeps both versions);
``codescientist_reruns.py`` applies it.

A run's outputs are read from its FINAL iteration (the last ``modal-python-<timestamp>``
directory that wrote ``modal-output/results.json``, as in v0.1). ``extract_run`` takes a
mapping from the path inside that ``modal-output/`` directory to the file's bytes:
``results.json``, ``to_save/**/*.json`` and ``log.json``.

Tiers, tried in order; the first tier holding at least one non-control bootstrap block
is used, and its controls with it:

1. ``results.json`` (exactly v0.1's source; a run recoverable in v0.1 is unchanged);
2. ``to_save/**/*.json`` (files the run saved for its report), pooled in path order;
3. ``log.json`` messages that print a bootstrap block (as JSON or as a Python dict).

Within the tier, candidates whose label contains "random" are positive controls (as in
v0.1); the rest are candidates for the primary comparison. One candidate is the primary.
Several: ``choose_primary`` (hypothesis, then experiment plan, by token matching); still
tied is ``ambiguous_primary`` and every candidate is kept for the per-comparison report.
"""

from __future__ import annotations

import ast
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any

SIG = ("mean_baseline", "mean_experimental", "p_value", "dataset_size")

# The rule as preregistered (``v0.2-prereg``) and as corrected before any v0.2 number was
# committed (``v0.2``; ``prereg/reproduce/cs_extraction_v0_2_deviations.md``). Both are
# run and reported.
RULES = {
    # scoring: how a candidate's distinctive words found in a text are scored;
    # item_names: how a list item is named in a label; ordered_key: whether the
    # cross-run comparison key keeps word order; zero_effect: whether an effect size is
    # dropped when it disagrees with the mean difference (in codescientist_reruns).
    "v0.2": {"scoring": "share", "item_names": "values", "ordered_key": True,
             "zero_effect": True},
    "v0.2-prereg": {"scoring": "count", "item_names": "fields", "ordered_key": False,
                    "zero_effect": False},
}

# ---------------------------------------------------------------------------------------
# Tolerant JSON


def decode(b: bytes) -> str | None:
    """Text of a file: UTF-8 (a BOM is dropped), else cp1252, else None."""
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


_NAMES = {"true": True, "false": False, "null": None, "True": True, "False": False,
          "None": None, "NaN": math.nan, "nan": math.nan, "Infinity": math.inf,
          "inf": math.inf}


def _lit(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and (node.value is None or
                                           isinstance(node.value, str | int | float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
        v = _lit(node.operand)
        if isinstance(v, bool) or not isinstance(v, int | float):
            raise ValueError("sign on a non-number")
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.Dict):
        if any(k is None for k in node.keys):
            raise ValueError("dict unpacking")
        keys = [_lit(k) for k in node.keys]
        if not all(isinstance(k, str | int | float) for k in keys):
            raise ValueError("unhashable key")
        return {str(k) if not isinstance(k, str) else k: _lit(v)
                for k, v in zip(keys, node.values, strict=True)}
    if isinstance(node, ast.List | ast.Tuple):
        return [_lit(x) for x in node.elts]
    raise ValueError(f"not a literal: {type(node).__name__}")


def literal(text: str) -> Any:
    """A restricted literal evaluator: JSON plus the Python spellings a run prints
    (single quotes, True/False/None, nan/inf, NaN/Infinity, trailing commas). Nothing is
    executed: only dict, list, tuple, string, number and the names above are accepted."""
    tree = ast.parse(text.strip(), mode="eval")
    return _lit(tree.body)


def load_tolerant(b: bytes) -> tuple[Any, str]:
    """Parse a results file. Returns ``(obj, how)``; ``how`` is ``json`` (plain parse),
    ``repaired`` (parsed only by the restricted literal evaluator), ``empty``,
    ``undecodable`` or ``unparseable`` (then ``obj`` is None)."""
    text = decode(b)
    if text is None:
        return None, "undecodable"
    if not text.strip():
        return None, "empty"
    try:
        return json.loads(text), "json"
    except ValueError:
        pass
    try:
        return literal(text), "repaired"
    except (ValueError, SyntaxError, RecursionError, MemoryError):
        return None, "unparseable"


def balanced(text: str, start: int) -> str | None:
    """The balanced ``{...}`` substring of ``text`` that opens at ``start`` (string-aware,
    single or double quotes), or None when it does not close."""
    if start >= len(text) or text[start] != "{":
        return None
    depth, quote, esc = 0, None, False
    for i in range(start, len(text)):
        c = text[i]
        if quote:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                quote = None
            continue
        if c in "\"'":
            quote = c
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


# ---------------------------------------------------------------------------------------
# Bootstrap blocks


@dataclass(frozen=True)
class Block:
    where: str        # file and key path (the v0.1 key path alone for results.json)
    label: str        # the path with list items named by their string fields, for matching
    numbers: tuple    # (mean_baseline, mean_experimental, p_value, dataset_size)
    raw: dict = field(compare=False, hash=False, repr=False)
    file: str = ""


def _short_strings(d: dict, item_names: str = "values") -> str:
    """A list item's name: its short string fields in key order, as values only
    (``boolean,full``) or as ``key=value`` (the preregistered form)."""
    keys = [k for k in sorted(d, key=str) if isinstance(d[k], str) and len(d[k]) <= 80]
    if item_names == "fields":
        return ",".join(f"{k}={d[k]}" for k in keys)
    return ",".join(d[k] for k in keys)


def find_blocks(obj: Any, path: tuple[str, ...] = (), lab: tuple[str, ...] = (),
                item_names: str = "values"):
    """Every dict holding the CodeScientist bootstrap signature, in v0.1's walk order:
    ``(key_path, label_path, block)``. In the label path a list item is named by its
    short string fields (``[boolean,full]``; ``item_names="fields"``:
    ``[baseline=boolean,experimental=full]``)."""
    if isinstance(obj, dict):
        if all(k in obj for k in SIG):
            yield ".".join(path), ".".join(lab), obj
        for k in sorted(obj, key=str):
            yield from find_blocks(obj[k], path + (str(k),), lab + (str(k),), item_names)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            name = _short_strings(v, item_names) if isinstance(v, dict) else ""
            yield from find_blocks(v, path + (f"[{i}]",), lab + (f"[{name}]" if name else "",),
                                   item_names)


def _key(b: dict) -> tuple:
    return tuple(json.dumps(b.get(k), sort_keys=True, default=str) for k in SIG)


def file_blocks(obj: Any, file: str, item_names: str = "values") -> list[Block]:
    out = []
    for path, lab, b in find_blocks(obj, item_names=item_names):
        where = path if file == "results.json" else f"{file}:{path}"
        out.append(Block(where, lab, _key(b), b, file))
    return out


def log_blocks(log: Any, item_names: str = "values") -> list[Block]:
    """Bootstrap blocks printed in ``log.json`` (a list of ``{type, runtime_sec,
    message}``). A message's first balanced ``{...}`` is parsed (JSON, else the restricted
    literal evaluator). Its label is the message text before the brace, without a final
    colon; when that is empty, the previous message's text if it ends with a colon. The
    same label printed again (a later pilot stage) replaces the earlier block; then
    identical numbers under several labels are kept once (first label)."""
    if not isinstance(log, list):
        return []
    by_label: dict[str, Block] = {}
    order: list[str] = []
    prev = ""
    for e in log:
        msg = e.get("message") if isinstance(e, dict) else None
        if not isinstance(msg, str):
            prev = ""
            continue
        i = msg.find("{")
        if i >= 0:
            sub = balanced(msg, i)
            obj = None
            if sub is not None:
                try:
                    obj = json.loads(sub)
                except ValueError:
                    try:
                        obj = literal(sub)
                    except (ValueError, SyntaxError, RecursionError, MemoryError):
                        obj = None
            if obj is not None:
                head = " ".join(msg[:i].split()).rstrip(":").strip()
                if not head and prev.endswith(":"):
                    head = prev.rstrip(":").strip()
                for path, lab, b in find_blocks(obj, item_names=item_names):
                    label = head + (f" / {lab}" if lab else "")
                    where = "log.json:" + head + (f" / {path}" if path else "")
                    blk = Block(where, label, _key(b), b, "log.json")
                    if label not in by_label:
                        order.append(label)
                    by_label[label] = blk
        prev = " ".join(msg.split())
    seen: set[tuple] = set()
    out = []
    for label in order:
        b = by_label[label]
        if b.numbers in seen:
            continue
        seen.add(b.numbers)
        out.append(b)
    return out


def is_control(where: str) -> bool:
    """A comparison against a random agent: its location (file, key path or log label)
    mentions "random". On a key path this is v0.1's rule."""
    return "random" in where.casefold()


# ---------------------------------------------------------------------------------------
# The primary-comparison rule

STOP = frozenset("""
a an and are as at be by for from in into is it its of on or than that the this to will
with vs versus bootstrap bootstrapping result results stat stats statistic statistics
statistical test tests comparison comparisons compare compared analysis analyses summary
metric metrics baseline baselines experimental experiment condition conditions value
values mean means json log save
""".split())


def words(text: str) -> list[str]:
    """Lowercase alphanumeric words in order of first appearance. Dropped: one-letter
    and digits-only words, and the fixed stop words (``STOP``: function words and the
    generic vocabulary of a statistics printout), before or after a final "s" is removed
    (from words longer than 3 letters not ending in "ss")."""
    out: list[str] = []
    for w in re.split(r"[^a-z0-9]+", (text or "").casefold()):
        if len(w) < 2 or w.isdigit() or w in STOP:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if w not in STOP and w not in out:
            out.append(w)
    return out


def tokens(text: str) -> set[str]:
    """The set of ``words(text)``."""
    return set(words(text))


def _match(labels: list[str], text: str, scoring: str) -> int | None:
    toks = [tokens(lab) for lab in labels]
    common = set.intersection(*toks) if toks else set()
    t = tokens(text)
    distinct = [tk - common for tk in toks]
    if scoring == "count":
        scores: list[float] = [len(d & t) for d in distinct]
    else:
        scores = [len(d & t) / len(d) if d else 0.0 for d in distinct]
    best = max(scores)
    if best > 0 and scores.count(best) == 1:
        return scores.index(best)
    return None


def choose_primary(labels: list[str], hypothesis: str, plan: str,
                   scoring: str = "share") -> tuple[int | None, str]:
    """Index of the primary comparison among several candidate labels, and the basis.

    Each candidate's distinctive words are its words minus those every candidate shares.
    Its score in a text is the share of its distinctive words that occur there
    (``scoring="count"``, as preregistered: their number, which favours longer names).
    A unique maximum above zero in the run's stated hypothesis wins (basis
    ``hypothesis``); otherwise in the experiment plan (``experiment_plan``); otherwise
    ``(None, "ambiguous")``: no choice is made."""
    if len(labels) == 1:
        return 0, "single"
    for text, basis in ((hypothesis, "hypothesis"), (plan, "experiment_plan")):
        i = _match(labels, text, scoring)
        if i is not None:
            return i, basis
    return None, "ambiguous"


def comparison_key(label: str, ordered: bool = True) -> tuple[str, ...]:
    """The words of a label, for matching the same comparison across two runs: in order
    (so ``A vs B`` does not match ``B vs A``), or as a sorted set (as preregistered)."""
    return tuple(words(label)) if ordered else tuple(sorted(tokens(label)))


# ---------------------------------------------------------------------------------------
# Other test outputs (recognised and classified, not turned into a record)

_PKEY = re.compile(r"^(?:.*_)?(?:p|p_?val(?:ue)?|pvalue)$", re.IGNORECASE)
_NKEY = re.compile(r"^(?:n|n_samples|num_samples|sample_size|dataset_size|count)$",
                   re.IGNORECASE)
_EKEY = re.compile(r"^(?:.*_)?(?:correlation|r|rho|t|t_?stat(?:istic)?|statistic|"
                   r"difference|diff|effect(?:_size)?|mean_diff(?:erence)?)$", re.IGNORECASE)


def other_tests(obj: Any) -> list[tuple[str, bool]]:
    """Dicts that report a p-value but are not bootstrap blocks: ``(key_path, complete)``,
    complete when the same dict also gives an estimate (correlation, statistic or
    difference) and an n. They are never turned into a record: the committed thresholds
    are those of the one-sided bootstrap test (see the module docstring of
    ``codescientist_reruns``)."""
    out = []

    def walk(o: Any, path: tuple[str, ...]):
        if isinstance(o, dict):
            if not all(k in o for k in SIG):
                keys = [str(k) for k in o if not isinstance(o[k], dict | list)]
                if any(_PKEY.match(k) for k in keys):
                    est = any(_EKEY.match(k) and not _PKEY.match(k) for k in keys)
                    n = any(_NKEY.match(k) for k in keys)
                    out.append((".".join(path), est and n))
            for k in sorted(o, key=str):
                walk(o[k], path + (str(k),))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + (f"[{i}]",))

    walk(obj, ())
    return out


# ---------------------------------------------------------------------------------------
# One run


@dataclass
class RunExtraction:
    status: str                        # ok | ambiguous_primary | no_test_output | ...
    tier: str | None = None            # results.json | to_save | log.json
    primary: Block | None = None
    basis: str | None = None           # single | hypothesis | experiment_plan
    candidates: list[Block] = field(default_factory=list)
    controls: list[Block] = field(default_factory=list)
    parse: dict[str, str] = field(default_factory=dict)   # file -> how it parsed
    other_tests: int = 0
    other_tests_complete: int = 0
    results_obj: Any = None
    source_obj: Any = None             # the parsed file the primary came from


def extract_run(files: dict[str, bytes], hypothesis: str = "", plan: str = "",
                rule: str = "v0.2") -> RunExtraction:
    """Apply the v0.2 tiers and the primary-comparison rule (``RULES[rule]``) to one
    run's final outputs."""
    cfg = RULES[rule]
    names = cfg["item_names"]
    parsed: dict[str, Any] = {}
    how: dict[str, str] = {}
    for name in sorted(files):
        obj, h = load_tolerant(files[name])
        how[name] = h
        if obj is not None:
            parsed[name] = obj
    tiers: list[tuple[str, list[Block]]] = []
    if "results.json" in parsed:
        tiers.append(("results.json", file_blocks(parsed["results.json"], "results.json",
                                                  names)))
    ts: list[Block] = []
    seen: set[tuple] = set()
    for name in sorted(n for n in parsed if n.startswith("to_save/")):
        for b in file_blocks(parsed[name], name, names):
            if b.numbers not in seen:
                seen.add(b.numbers)
                ts.append(b)
    tiers.append(("to_save", ts))
    if "log.json" in parsed:
        tiers.append(("log.json", log_blocks(parsed["log.json"], names)))
    res = RunExtraction(status="", parse=how, results_obj=parsed.get("results.json"))
    for tier, blocks in tiers:
        cands = [b for b in blocks if not is_control(b.where)]
        if not cands:
            continue
        res.tier = tier
        res.candidates = cands
        res.controls = [b for b in blocks if is_control(b.where)]
        i, basis = choose_primary([b.label for b in cands], hypothesis, plan, cfg["scoring"])
        res.basis = basis
        if i is None:
            res.status = "ambiguous_primary"
            return res
        res.primary = cands[i]
        res.source_obj = parsed.get(cands[i].file)
        res.status = "ok"
        return res
    for name in sorted(parsed):
        if name == "log.json":
            continue
        for _, complete in other_tests(parsed[name]):
            res.other_tests += 1
            res.other_tests_complete += complete
    if res.other_tests_complete:
        res.status = "other_test_output"
    elif res.other_tests:
        res.status = "test_output_incomplete"
    elif not any(n != "log.json" for n in parsed):
        res.status = "unreadable_results_file"
    else:
        res.status = "no_test_output"
    return res
