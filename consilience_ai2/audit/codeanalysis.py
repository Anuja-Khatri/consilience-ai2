"""Static reads of the experiment code with Python's ``ast``. No code is ever executed.

Four questions are asked of the code:

- ``numeric_literals``: every number written in the code (and in plain string constants,
  never in format specs such as ``:.3f``), with its line. A1 accepts a printed number
  that equals a code literal as "from the code" (a design constant), not "from the
  output"; R4 asks which literals sit on the output path.
- ``n_constants`` (A2): integer constants assigned to names that look like sample sizes
  (``N_EPISODES = 50``, ``num_samples = 100``, ``{"PILOT": 25}``) and ``range(N)`` bounds.
- ``column_references`` (A3): string column names read from data frames (``df["x"]``,
  ``df[["a", "b"]]``, ``df.loc[:, "x"]``, ``groupby("x")``, formula strings ``"y ~ x"``),
  and the columns the code itself creates (assigned, renamed, ``assign(x=...)``).
- ``unused_components`` (R5): a flow-insensitive, over-approximate backward slice from
  every output sink (print, logging calls, ``write``, ``json.dump``, ``savefig``,
  ``to_csv``...). A user-defined top-level function or class that is used somewhere but
  neither contains a sink nor appears in that slice is "built but unused". Because the
  slice over-approximates every data path (attributes and subscripts collapse to their
  base name, every argument of a call may be mutated by it, branch conditions count as
  dependencies), a component outside it is on no path to anything printed or saved,
  except through dynamic features the analysis cannot see (``eval``, ``exec``,
  ``getattr`` with a computed name, ``globals()``); code that uses those is reported as
  uncheckable instead. The analysis is sound in that direction and incomplete: a
  component whose output is logged anywhere is "used", even if the reported metric does
  not depend on it.
- ``figure_text_lines`` (A1, rules v0.2): lines of plotting calls (``plot``, ``bar``,
  ``text``, ``annotate``, ``title``, ``legend``, axis labels...) that write a formatted
  value into figure text (an f-string with a replacement field, ``str.format`` or ``%``
  formatting), in code that also calls ``savefig``. A number such a run prints only in a
  saved figure is in an output the audit cannot read.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from consilience_ai2.audit.parse import NUM

_NUM_IN_STR = re.compile(r"(?<![A-Za-z0-9_.])" + NUM)

N_NAME_RX = re.compile(
    r"(?:^|_)(?:n|num|number|count|size|samples?|episodes?|trials?|games?|runs?|seeds?|"
    r"iterations?|items?|tasks?|examples?|instances?|scenarios?|participants?|targets?|"
    r"predictions?|steps?|rows?|batch(?:es)?|repeats?|reps?|folds?|values?)(?:_|$)",
    re.IGNORECASE,
)
_PILOT_KEY_RX = re.compile(r"^(?:MINI_PILOT|PILOT|FULL_EXPERIMENT|FULL|DEBUG|TEST)$")
RESULT_NAME_RX = re.compile(
    r"(?:result|score|accuracy|acc|mean|avg|average|rate|metric|p_?val|pvalue|success|auc|"
    r"f1|precision|recall|effect|corr|correlation|stat|improvement|difference|delta|gain|"
    r"performance|loss|error)",
    re.IGNORECASE,
)
SINK_FUNCS = {"print", "pprint"}
SINK_ATTRS = {
    "logMessage", "log", "info", "warning", "warn", "error", "debug", "critical", "exception",
    "write", "writelines", "dump", "dumps", "savefig", "to_csv", "to_json", "to_excel",
    "to_parquet", "to_pickle", "writerow", "writerows", "save", "imwrite", "print",
}
DYNAMIC_FUNCS = {"eval", "exec", "globals", "locals", "setattr", "__import__", "vars"}
OUTPUT_NAME_RX = re.compile(r"(?:plot|save|log|print|visual|report|write|dump|display|show)",
                            re.IGNORECASE)
_DF_METHODS_COLS = {"groupby", "sort_values", "set_index", "pivot", "pivot_table", "nlargest",
                    "nsmallest", "value_counts", "drop_duplicates"}
_DF_KW_COLS = {"by", "index", "columns", "values", "subset", "on", "x", "y", "hue"}
_FRAME_METHODS = {"copy", "dropna", "fillna", "query", "sample", "head", "tail", "sort_values",
                  "sort_index", "reset_index", "merge", "join", "assign", "drop", "rename",
                  "drop_duplicates", "astype", "replace", "set_index", "nlargest", "nsmallest",
                  "filter", "where", "mask", "select_dtypes", "reindex", "interpolate", "clip",
                  "round", "convert_dtypes", "infer_objects", "pipe"}
# Methods assumed not to mutate their receiver (Python and pandas semantics) unless called
# with inplace=True. R5 uses this list when deciding whether a user function can mutate an
# argument; it is the analysis's one stated assumption beyond the language itself.
NONMUTATING_METHODS = {
    "copy", "get", "keys", "values", "items", "count", "index", "mean", "median", "sum", "std",
    "var", "min", "max", "describe", "head", "tail", "groupby", "agg", "aggregate", "apply",
    "value_counts", "unique", "nunique", "isna", "isnull", "notna", "notnull", "corr", "cov",
    "to_dict", "to_list", "tolist", "to_numpy", "astype", "query", "dropna", "fillna",
    "sort_values", "reset_index", "rename", "drop", "replace", "merge", "join", "sample",
    "startswith", "endswith", "lower", "upper", "strip", "split", "format", "round", "abs",
    "any", "all", "idxmax", "idxmin", "quantile", "cumsum", "shift", "diff", "pct_change",
    "rank", "nlargest", "nsmallest", "isin", "between", "map", "where", "mask", "select_dtypes",
}
NONMUTATING_FUNCS = {
    "len", "print", "str", "int", "float", "bool", "isinstance", "type", "repr", "sorted",
    "list", "tuple", "dict", "set", "frozenset", "sum", "min", "max", "abs", "round",
    "enumerate", "zip", "range", "hasattr", "id", "hash", "any", "all", "iter", "format",
}
# Plotting calls whose arguments become text in a figure (matplotlib / seaborn names).
FIGURE_TEXT_CALLS = {
    "plot", "bar", "barh", "scatter", "hist", "errorbar", "pie", "boxplot", "violinplot",
    "text", "annotate", "figtext", "title", "suptitle", "set_title", "legend", "xlabel",
    "ylabel", "set_xlabel", "set_ylabel", "table", "bar_label", "set_text", "lineplot",
    "barplot", "scatterplot", "histplot", "heatmap",
}
_FORMULA_FUNCS = {"ols", "logit", "glm", "mixedlm", "from_formula", "poisson", "probit",
                  "quantreg", "gee", "wls", "negativebinomial"}
_FORMULA_SKIP = {"C", "I", "Q", "np", "log", "exp", "sqrt", "center", "scale", "standardize",
                 "bs", "cr", "poly", "Treatment", "Sum", "Diff", "T", "abs", "pow"}


@dataclass(frozen=True)
class Literal:
    value: str           # the number as written
    line: int
    on_output_path: bool
    context: str         # "sink-arg", "result-assign", "result-dict", "result-return", "other"
    name: str | None = None


@dataclass
class CodeFacts:
    ok: bool
    error: str | None = None
    literals: list[Literal] = field(default_factory=list)
    n_constants: dict[int, int] = field(default_factory=dict)        # value -> first line
    columns_read: dict[str, int] = field(default_factory=dict)       # name -> first line
    columns_created: set[str] = field(default_factory=set)
    uses_dummies: bool = False
    unused_components: list[tuple[str, int, str]] = field(default_factory=list)
    components_checked: int = 0
    r5_uncheckable: str | None = None
    figure_text_lines: list[int] = field(default_factory=list)


def _call_name(func: ast.AST) -> tuple[str | None, str | None]:
    """(simple function name, attribute name) of a call target."""
    if isinstance(func, ast.Name):
        return func.id, None
    if isinstance(func, ast.Attribute):
        return None, func.attr
    return None, None


def _is_sink(call: ast.Call) -> bool:
    name, attr = _call_name(call.func)
    return (name in SINK_FUNCS) or (attr in SINK_ATTRS)


def _numbers_in_expr(expr: ast.AST) -> list[tuple[str, int]]:
    """Numbers written in an expression: numeric constants and numbers inside string
    constants, never inside f-string format specs."""
    out: list[tuple[str, int]] = []

    def visit(n: ast.AST) -> None:
        if isinstance(n, ast.JoinedStr):
            for v in n.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out.extend((m.group(0), v.lineno) for m in _NUM_IN_STR.finditer(v.value))
                elif isinstance(v, ast.FormattedValue):
                    visit(v.value)  # skip v.format_spec
            return
        if isinstance(n, ast.Constant):
            if isinstance(n.value, bool):
                return
            if isinstance(n.value, int | float):
                out.append((repr(n.value), n.lineno))
            elif isinstance(n.value, str):
                out.extend((m.group(0), n.lineno) for m in _NUM_IN_STR.finditer(n.value))
            return
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(
                n.operand, ast.Constant) and isinstance(n.operand.value, int | float) and not \
                isinstance(n.operand.value, bool):
            out.append(("-" + repr(n.operand.value), n.lineno))
            return
        for c in ast.iter_child_nodes(n):
            visit(c)

    visit(expr)
    return out


def _target_names(t: ast.AST) -> list[str]:
    if isinstance(t, ast.Name):
        return [t.id]
    if isinstance(t, ast.Attribute):
        return [t.attr]
    if isinstance(t, ast.Subscript):
        s = t.slice
        if isinstance(s, ast.Constant) and isinstance(s.value, str):
            return [s.value]
        return _target_names(t.value)
    if isinstance(t, ast.Tuple | ast.List):
        return [n for e in t.elts for n in _target_names(e)]
    return []


def _const_number(v: ast.AST) -> str | None:
    if isinstance(v, ast.Constant) and isinstance(v.value, int | float) and not isinstance(
            v.value, bool):
        return repr(v.value)
    if isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.USub):
        inner = _const_number(v.operand)
        return None if inner is None else "-" + inner
    return None


def _literals(tree: ast.AST) -> list[Literal]:
    out: dict[tuple[str, int, str], Literal] = {}

    def add(value: str, line: int, on_path: bool, ctx: str, name: str | None = None) -> None:
        key = (value, line, ctx)
        if key not in out:
            out[key] = Literal(value, line, on_path, ctx, name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_sink(node):
            for a in list(node.args) + [k.value for k in node.keywords]:
                for v, ln in _numbers_in_expr(a):
                    add(v, ln, True, "sink-arg")
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            val = node.value
            if val is None:
                continue
            num = _const_number(val)
            names = [n for t in targets for n in _target_names(t)]
            if num is not None and any(RESULT_NAME_RX.search(n) for n in names):
                add(num, node.lineno, True, "result-assign", names[0])
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values, strict=False):
                if isinstance(k, ast.Constant) and isinstance(k.value, str) and \
                        RESULT_NAME_RX.search(k.value):
                    num = _const_number(v)
                    if num is not None:
                        add(num, v.lineno, True, "result-dict", k.value)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and \
                RESULT_NAME_RX.search(node.name):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    num = _const_number(sub.value)
                    if num is not None:
                        add(num, sub.lineno, True, "result-return", node.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float) and \
                not isinstance(node.value, bool):
            v = repr(node.value)
            if not any(k[0] == v and k[1] == node.lineno for k in out):
                add(v, node.lineno, False, "other")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for m in _NUM_IN_STR.finditer(node.value):
                if not any(k[0] == m.group(0) and k[1] == node.lineno for k in out):
                    add(m.group(0), node.lineno, False, "other")
    return sorted(out.values(), key=lambda x: (x.line, x.value, x.context))


def _n_constants(tree: ast.AST) -> dict[int, int]:
    out: dict[int, int] = {}

    def add(v: object, line: int) -> None:
        if isinstance(v, int) and not isinstance(v, bool) and v >= 2:
            out.setdefault(v, line)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = (node.targets if isinstance(node, ast.Assign) else [node.target])
            names = [n for t in targets for n in _target_names(t)]
            val = node.value
            if val is not None and isinstance(val, ast.Constant) and \
                    any(N_NAME_RX.search(n) for n in names):
                add(val.value, node.lineno)
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values, strict=False):
                if isinstance(k, ast.Constant) and isinstance(k.value, str) and (
                        N_NAME_RX.search(k.value) or _PILOT_KEY_RX.match(k.value)) and \
                        isinstance(v, ast.Constant):
                    add(v.value, v.lineno)
        elif isinstance(node, ast.keyword) and node.arg and N_NAME_RX.search(node.arg) and \
                isinstance(node.value, ast.Constant):
            add(node.value.value, node.value.lineno)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                node.func.id == "range":
            for a in node.args:
                if isinstance(a, ast.Constant):
                    add(a.value, a.lineno)
    return out


def _root_name(e: ast.AST) -> str | None:
    while True:
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.Attribute | ast.Subscript):
            e = e.value
        elif isinstance(e, ast.Call):
            e = e.func
        else:
            return None


def _str_consts(e: ast.AST) -> list[str]:
    if isinstance(e, ast.Constant) and isinstance(e.value, str):
        return [e.value]
    if isinstance(e, ast.List | ast.Tuple | ast.Set):
        return [x.value for x in e.elts if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    return []


def _columns(tree: ast.AST) -> tuple[dict[str, int], set[str], bool]:
    df_names: set[str] = set()
    df_rx = re.compile(r"^(?:df|data|dataset|frame)\w*$", re.IGNORECASE)
    assigns: list[tuple[list[str], ast.AST]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            assigns.append((names, node.value))
            for n in names:
                if df_rx.match(n):
                    df_names.add(n)
    for names, val in assigns:  # read_* / DataFrame constructors
        if isinstance(val, ast.Call):
            nm, at = _call_name(val.func)
            if (at or nm or "").startswith("read_") or (at or nm) == "DataFrame":
                df_names.update(names)
    def frame_like(e: ast.AST) -> bool:
        """A frame with the same columns: a frame name, a row or column-list selection,
        or a frame-preserving method (not groupby/agg, whose results are indexed by
        group values)."""
        if isinstance(e, ast.Name):
            return e.id in df_names
        if isinstance(e, ast.Subscript):
            v = e.value
            if isinstance(v, ast.Attribute) and v.attr in ("loc", "iloc"):
                return frame_like(v.value)
            s = e.slice
            single = isinstance(s, ast.Constant) and isinstance(s.value, str)
            return frame_like(v) and not single
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute):
            if e.func.attr in _FRAME_METHODS and frame_like(e.func.value):
                return True
            if e.func.attr == "concat" and e.args and isinstance(e.args[0], ast.List | ast.Tuple):
                return any(frame_like(x) for x in e.args[0].elts)
        return False

    changed = True
    while changed:  # derived frames: df2 = df[mask], d = df.dropna(), m = df.merge(...)
        changed = False
        for names, val in assigns:
            if frame_like(val) and not set(names) <= df_names:
                df_names.update(names)
                changed = True
    read: dict[str, int] = {}
    created: set[str] = set()
    dummies = False

    def add_read(cols: list[str], line: int) -> None:
        for c in cols:
            read.setdefault(c, line)

    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and _root_name(node.value) in df_names:
            base = node.value
            s = node.slice
            if isinstance(base, ast.Attribute) and base.attr in ("loc",):
                if isinstance(s, ast.Tuple) and len(s.elts) == 2:
                    cols = _str_consts(s.elts[1])
                else:
                    cols = []
            elif isinstance(base, ast.Attribute) and base.attr in ("iloc", "at", "iat"):
                cols = []
            elif isinstance(base, ast.Name | ast.Subscript | ast.Call) or (
                    isinstance(base, ast.Attribute) and base.attr not in ("str", "dt", "cat")):
                cols = _str_consts(s)
            else:
                cols = []
            if isinstance(node.ctx, ast.Store):
                created.update(cols)
            else:
                add_read(cols, node.lineno)
        elif isinstance(node, ast.Call):
            nm, at = _call_name(node.func)
            fname = at or nm or ""
            if fname == "get_dummies" or fname == "OneHotEncoder":
                dummies = True
            if at and _root_name(node.func) in df_names:
                if at in _DF_METHODS_COLS:
                    for a in node.args[:1]:
                        add_read(_str_consts(a), node.lineno)
                    for k in node.keywords:
                        if k.arg in _DF_KW_COLS:
                            add_read(_str_consts(k.value), node.lineno)
                elif at == "dropna":
                    for k in node.keywords:
                        if k.arg == "subset":
                            add_read(_str_consts(k.value), node.lineno)
                elif at == "assign":
                    created.update(k.arg for k in node.keywords if k.arg)
                elif at == "rename":
                    for k in node.keywords:
                        if k.arg == "columns" and isinstance(k.value, ast.Dict):
                            created.update(v.value for v in k.value.values
                                           if isinstance(v, ast.Constant) and isinstance(v.value, str))
                elif at in ("agg", "aggregate"):
                    created.update(k.arg for k in node.keywords if k.arg)
                elif at == "reset_index":
                    created.add("index")
                elif at == "melt":
                    created.update({"variable", "value"})
            if fname.lower() in _FORMULA_FUNCS:
                for a in list(node.args[:1]) + [k.value for k in node.keywords if k.arg == "formula"]:
                    for f in _str_consts(a):
                        if "~" in f:
                            for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", f):
                                if tok not in _FORMULA_SKIP:
                                    add_read([tok], node.lineno)
    return read, created, dummies


# --------------------------------------------------------------------------- R5 slicing


def _own_exprs(st: ast.stmt) -> list[ast.AST]:
    """The expressions a statement evaluates itself, excluding nested statement bodies."""
    if isinstance(st, ast.For | ast.AsyncFor):
        return [st.iter, st.target]
    if isinstance(st, ast.While | ast.If):
        return [st.test]
    if isinstance(st, ast.With | ast.AsyncWith):
        return [it.context_expr for it in st.items]
    if isinstance(st, ast.Try):
        return []
    if hasattr(ast, "Match") and isinstance(st, ast.Match):
        return [st.subject]
    return [st]


def _mutated_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[list[str], set[str]]:
    """(parameter names in order, the parameters the function may mutate).

    A parameter may be mutated when, anywhere in the body (nested functions included):
    it is the base of an attribute or subscript store, an augmented assignment or a
    ``del``; it receives a method call not in NONMUTATING_METHODS, or any method call
    with ``inplace=True``; it is passed to any call other than NONMUTATING_FUNCS; or it
    is aliased (assigned, sliced or attribute-accessed into another name, which might
    then be mutated). Anything else leaves it unchanged."""
    a = fn.args
    params = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    pset = set(params)
    mut: set[str] = set()

    def base(t: ast.AST) -> str | None:
        while isinstance(t, ast.Attribute | ast.Subscript | ast.Starred):
            t = t.value
        return t.id if isinstance(t, ast.Name) else None

    for n in ast.walk(fn):
        if isinstance(n, ast.Assign | ast.AugAssign | ast.AnnAssign | ast.Delete):
            targets = (n.targets if isinstance(n, ast.Assign | ast.Delete) else [n.target])
            for t in targets:
                for x in ast.walk(t):
                    if isinstance(x, ast.Attribute | ast.Subscript):
                        b = base(x)
                        if b in pset:
                            mut.add(b)
                if isinstance(n, ast.AugAssign) and isinstance(t, ast.Name) and t.id in pset:
                    mut.add(t.id)
            val = getattr(n, "value", None)
            if val is not None and isinstance(val, ast.Name | ast.Attribute | ast.Subscript):
                b = base(val)
                if b in pset:
                    mut.add(b)  # aliased
        elif isinstance(n, ast.Call):
            inplace = any(k.arg == "inplace" and not (isinstance(k.value, ast.Constant) and
                                                      k.value.value is False)
                          for k in n.keywords)
            if isinstance(n.func, ast.Attribute):
                b = base(n.func.value)
                if b in pset and (inplace or n.func.attr not in NONMUTATING_METHODS):
                    mut.add(b)
            nm, _ = _call_name(n.func)
            if nm not in NONMUTATING_FUNCS:
                for arg in list(n.args) + [k.value for k in n.keywords]:
                    if isinstance(arg, ast.Name | ast.Starred) or (
                            isinstance(arg, ast.Attribute | ast.Subscript)):
                        b = base(arg)
                        if b in pset:
                            mut.add(b)
        elif isinstance(n, ast.For | ast.With | ast.comprehension):
            pass
    return params, mut


class _Slicer:
    """Flow-insensitive dependency graph over qualified names (see module docstring)."""

    def __init__(self, tree: ast.Module):
        self.tree = tree
        self.edges: dict[str, set[str]] = {}
        self.sink_reads: set[str] = set()
        self.components: dict[str, tuple[int, str]] = {}   # name -> (line, kind)
        self.contains_sink: set[str] = set()
        self.referenced: set[str] = set()
        self.entry_points: set[str] = set()
        self.dynamic = False
        self.mutated_params: dict[str, tuple[list[str], set[str]]] = {}
        for st in tree.body:
            if isinstance(st, ast.FunctionDef | ast.AsyncFunctionDef):
                self.mutated_params[st.name] = _mutated_params(st)
        for st in tree.body:
            if isinstance(st, ast.FunctionDef | ast.AsyncFunctionDef):
                self.components[st.name] = (st.lineno, "function")
            elif isinstance(st, ast.ClassDef):
                self.components[st.name] = (st.lineno, "class")

    def edge(self, target: str, sources: set[str]) -> None:
        if sources:
            self.edges.setdefault(target, set()).update(sources)

    def q(self, scope: str, local: set[str], name: str) -> str:
        if name in self.components and name not in local:
            return "def:" + name
        return f"{scope}:{name}" if name in local else f"<module>:{name}"

    def reads(self, e: ast.AST | None, scope: str, local: set[str]) -> set[str]:
        out: set[str] = set()
        if e is None:
            return out
        for n in ast.walk(e):
            if isinstance(n, ast.Name):
                out.add(self.q(scope, local, n.id))
                if n.id in self.components:
                    self.referenced.add(n.id)
            elif isinstance(n, ast.Call):
                nm, at = _call_name(n.func)
                if nm in DYNAMIC_FUNCS or (nm == "getattr" and len(n.args) >= 2 and
                                           not isinstance(n.args[1], ast.Constant)):
                    self.dynamic = True
        return out

    @staticmethod
    def base(t: ast.AST) -> str | None:
        while isinstance(t, ast.Attribute | ast.Subscript | ast.Starred):
            t = t.value
        return t.id if isinstance(t, ast.Name) else None

    def locals_of(self, fn: ast.AST) -> set[str]:
        loc: set[str] = set()
        glob: set[str] = set()
        if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            a = fn.args
            for arg in a.posonlyargs + a.args + a.kwonlyargs:
                loc.add(arg.arg)
            if a.vararg:
                loc.add(a.vararg.arg)
            if a.kwarg:
                loc.add(a.kwarg.arg)
        body = fn.body if isinstance(fn.body, list) else [fn.body]
        for st in body:
            for n in ast.walk(st):
                if isinstance(n, ast.Global | ast.Nonlocal):
                    glob.update(n.names)
                elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    loc.add(n.id)
                elif isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    loc.add(n.name)
                elif isinstance(n, ast.alias):
                    loc.add((n.asname or n.name).split(".")[0])
                elif isinstance(n, ast.ExceptHandler) and n.name:
                    loc.add(n.name)
        return loc - glob

    def block(self, body: list[ast.stmt], scope: str, local: set[str], ctrl: set[str],
              owner: str | None) -> None:
        for st in body:
            self.stmt(st, scope, local, ctrl, owner)

    def call_effects(self, call: ast.Call, scope: str, local: set[str], ctrl: set[str],
                     owner: str | None) -> None:
        if _is_sink(call):
            self.sink_reads |= self.reads(call, scope, local) | ctrl
            if owner:
                self.contains_sink.add(owner)
        allr = self.reads(call, scope, local) | ctrl
        targets: set[str] = set()
        if isinstance(call.func, ast.Attribute):
            b = self.base(call.func.value)
            if b:
                targets.add(self.q(scope, local, b))
        for a in list(call.args) + [k.value for k in call.keywords]:
            b = self.base(a)
            if b:
                targets.add(self.q(scope, local, b))
        nm, _ = _call_name(call.func)
        if nm in self.components:
            self.referenced.add(nm)
            # parameters of the callee receive the arguments
            self.edge("param:" + nm, allr)
            mut = self.mutated_params.get(nm)
            if mut is not None:
                # a user function can only change the arguments bound to parameters it
                # may mutate (see _mutated_params); others are not targets
                targets = set()
                if isinstance(call.func, ast.Attribute):
                    b = self.base(call.func.value)
                    if b:
                        targets.add(self.q(scope, local, b))
                params = mut[0]
                for i, a in enumerate(call.args):
                    if isinstance(a, ast.Starred) or i >= len(params) or params[i] in mut[1]:
                        b = self.base(a)
                        if b:
                            targets.add(self.q(scope, local, b))
                for k in call.keywords:
                    if k.arg is None or k.arg in mut[1] or k.arg not in params:
                        b = self.base(k.value)
                        if b:
                            targets.add(self.q(scope, local, b))
        for t in targets:
            if not t.startswith("def:"):
                self.edge(t, allr)

    def stmt(self, st: ast.stmt, scope: str, local: set[str], ctrl: set[str],
             owner: str | None) -> None:
        if isinstance(st, ast.FunctionDef | ast.AsyncFunctionDef):
            if scope == "<module>":
                self.function(st, st.name, st.name)
            else:
                # a nested function is inlined into its enclosing scope (over-approximate)
                inner = local | self.locals_of(st)
                self.block(st.body, scope, inner, ctrl, owner)
                body_reads: set[str] = set()
                for b in st.body:
                    body_reads |= self.reads(b, scope, inner)
                self.edge(self.q(scope, local, st.name), body_reads)
            return
        if isinstance(st, ast.ClassDef):
            for b in st.body:
                if isinstance(b, ast.FunctionDef | ast.AsyncFunctionDef):
                    self.function(b, st.name + "." + b.name, st.name, cls=st.name)
                else:
                    self.stmt(b, st.name, set(), set(), st.name)
            reads = set()
            for b in st.bases:
                reads |= self.reads(b, scope, local)
            self.edge("def:" + st.name, reads | {"self:" + st.name})
            return
        # visit every call in the statement's own expressions (not nested bodies)
        for e in _own_exprs(st):
            for n in ast.walk(e):
                if isinstance(n, ast.Call):
                    self.call_effects(n, scope, local, ctrl, owner)
        if isinstance(st, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = st.targets if isinstance(st, ast.Assign) else [st.target]
            src = self.reads(st.value, scope, local) | ctrl
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name | ast.Attribute | ast.Subscript):
                        b = self.base(n)
                        if b:
                            tq = self.q(scope, local, b)
                            extra = self.reads(t, scope, local) - {tq}
                            if b == "self" and owner:
                                tq = "self:" + owner
                            self.edge(tq, src | extra)
        elif isinstance(st, ast.Return):
            self.edge("ret:" + scope, self.reads(st.value, scope, local) | ctrl)
        elif isinstance(st, ast.Expr):
            if isinstance(st.value, ast.Yield | ast.YieldFrom):
                self.edge("ret:" + scope, self.reads(st.value, scope, local) | ctrl)
        elif isinstance(st, ast.For | ast.AsyncFor):
            src = self.reads(st.iter, scope, local) | ctrl
            for n in ast.walk(st.target):
                if isinstance(n, ast.Name):
                    self.edge(self.q(scope, local, n.id), src)
            self.block(st.body, scope, local, ctrl | src, owner)
            self.block(st.orelse, scope, local, ctrl | src, owner)
        elif isinstance(st, ast.While | ast.If):
            c = ctrl | self.reads(st.test, scope, local)
            self.block(st.body, scope, local, c, owner)
            self.block(st.orelse, scope, local, c, owner)
        elif isinstance(st, ast.With | ast.AsyncWith):
            for it in st.items:
                src = self.reads(it.context_expr, scope, local) | ctrl
                if it.optional_vars is not None:
                    b = self.base(it.optional_vars)
                    if b:
                        self.edge(self.q(scope, local, b), src)
            self.block(st.body, scope, local, ctrl, owner)
        elif isinstance(st, ast.Try):
            self.block(st.body, scope, local, ctrl, owner)
            for h in st.handlers:
                self.block(h.body, scope, local, ctrl, owner)
            self.block(st.orelse, scope, local, ctrl, owner)
            self.block(st.finalbody, scope, local, ctrl, owner)
        elif hasattr(ast, "Match") and isinstance(st, ast.Match):
            c = ctrl | self.reads(st.subject, scope, local)
            for case in st.cases:
                self.block(case.body, scope, local, c, owner)

    def function(self, fn: ast.FunctionDef | ast.AsyncFunctionDef, scope: str,
                 owner: str | None, cls: str | None = None) -> None:
        local = self.locals_of(fn)
        # parameters depend on what callers pass (over-approximate: any call of the
        # top-level owner)
        params = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
        root = scope.split(".")[0]
        for p in params:
            src = {"param:" + root}
            if cls is not None and p == params[0]:
                src = {"self:" + cls}
            self.edge(f"{scope}:{p}", src)
        for d in fn.args.defaults + fn.args.kw_defaults:
            if d is not None:
                for p in params:
                    self.edge(f"{scope}:{p}", self.reads(d, scope, local))
        self.block(fn.body, scope, local, set(), owner)
        # self.x inside methods is the instance state of the class
        if cls is not None and params:
            self.edge("self:" + cls, {f"{scope}:{params[0]}"})
            self.edge(f"{scope}:{params[0]}", {"self:" + cls})
        target = "def:" + (cls or root)
        self.edge(target, {"ret:" + scope})
        if cls is not None:
            self.edge("self:" + cls, {"ret:" + scope})

    def run(self) -> None:
        for st in ast.walk(self.tree):
            # a component called as a bare statement at module level is an entry point
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
                nm, _ = _call_name(st.value.func)
                if nm in self.components and self._at_module_level(st):
                    self.entry_points.add(nm)
        self.block(self.tree.body, "<module>", set(), set(), None)

    def _at_module_level(self, node: ast.AST) -> bool:
        def contains(body: list[ast.stmt]) -> bool:
            for st in body:
                if st is node:
                    return True
                if isinstance(st, ast.If | ast.With | ast.Try) and contains(
                        getattr(st, "body", []) + getattr(st, "orelse", []) +
                        getattr(st, "finalbody", [])):
                    return True
            return False
        return contains(self.tree.body)

    def slice(self) -> set[str]:
        seen: set[str] = set()
        stack = list(self.sink_reads)
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.edges.get(n, ()))
        return seen


def _unused(tree: ast.Module) -> tuple[list[tuple[str, int, str]], int, str | None]:
    sl = _Slicer(tree)
    sl.run()
    if sl.dynamic:
        return [], 0, "code uses eval/exec/globals/setattr/dynamic getattr; data flow not decidable"
    if not sl.sink_reads:
        return [], 0, "no output sink (print, logging, write, dump, savefig) found"
    reached = sl.slice()
    out = []
    checked = 0
    for name, (line, kind) in sorted(sl.components.items(), key=lambda kv: kv[1][0]):
        if name not in sl.referenced:
            continue  # defined but never used: dead code, not "built"
        if name in sl.contains_sink or OUTPUT_NAME_RX.search(name) or name in sl.entry_points:
            continue  # it prints or saves itself, or it is the program's entry point
        checked += 1
        if "def:" + name not in reached:
            out.append((name, line, kind))
    return out, checked, None


def _formats_a_value(e: ast.AST) -> bool:
    """True when ``e`` contains a string built from a runtime value: an f-string with a
    replacement field, ``"...".format(...)`` or ``"..." % x``."""
    for n in ast.walk(e):
        if isinstance(n, ast.JoinedStr) and any(isinstance(v, ast.FormattedValue)
                                                for v in n.values):
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and \
                n.func.attr == "format" and isinstance(n.func.value, ast.Constant) and \
                isinstance(n.func.value.value, str):
            return True
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and \
                isinstance(n.left, ast.Constant) and isinstance(n.left.value, str):
            return True
    return False


def _figure_text_lines(tree: ast.AST) -> list[int]:
    """Lines of plotting calls that write a formatted value into a figure, when the code
    saves figures (``savefig``); empty otherwise."""
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    if not any(_call_name(c.func)[1] == "savefig" or _call_name(c.func)[0] == "savefig"
               for c in calls):
        return []
    lines = set()
    for c in calls:
        name, attr = _call_name(c.func)
        if (attr or name) not in FIGURE_TEXT_CALLS:
            continue
        if any(_formats_a_value(a) for a in list(c.args) + [k.value for k in c.keywords]):
            lines.add(c.lineno)
    return sorted(lines)


def analyse(code: str) -> CodeFacts:
    """All static facts about ``code``; ``ok`` is False when it does not parse."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        return CodeFacts(ok=False, error=f"{type(exc).__name__}: {exc}")
    facts = CodeFacts(ok=True)
    facts.literals = _literals(tree)
    facts.n_constants = _n_constants(tree)
    facts.columns_read, facts.columns_created, facts.uses_dummies = _columns(tree)
    facts.figure_text_lines = _figure_text_lines(tree)
    try:
        facts.unused_components, facts.components_checked, facts.r5_uncheckable = _unused(tree)
    except RecursionError:  # pragma: no cover - pathological nesting
        facts.r5_uncheckable = "code too deeply nested for the slicer"
    return facts
