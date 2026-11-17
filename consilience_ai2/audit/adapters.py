"""Adapters: native run files to a ``Run`` of ``Node``s.

AutoDiscovery (``load_autodiscovery``)
    A local ``--out_dir`` (``mcts_node_<level>_<idx>.json`` files, else
    ``mcts_nodes_all.json``, else ``mcts_nodes.json``), plus ``args.json`` and the dataset
    metadata; or a hosted run's ``results.json`` (``{"run": ..., "experiments": [...]}``,
    from ``asta autodiscovery results``). Nodes at level 0 and 1 (root and seed level) and
    nodes with no hypothesis hold no experiment and are skipped, as asta-plugins'
    ``runlog.py`` does. Node fields follow ``MCTSNode.to_dict``.

CodeScientist (``load_codescientist``)
    An experiment directory (``history.json``, ``modal-python-<ts>/`` per debug
    iteration, ``report/report.tex``). The last ``modal-python-*`` directory is the run
    that produced the report; its ``main.py`` is the code and its ``modal-output/``
    (``stdout.python.txt``, ``log.json``, ``results.json``) is the evidence. The claim is
    ``report/report.tex`` (else ``report-watermarked/report.tex``, else the summary in
    ``history.json``). A directory of experiment directories gives one node each. Reads a
    real directory or a prefix inside a zip archive, without extracting it.
"""

from __future__ import annotations

import json
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from consilience_ai2.audit.model import CLAIM, CODE, CONTEXT, EVIDENCE, Node, Run, TextField
from consilience_ai2.core.hashing import sha256_bytes

_NODE_FILE = re.compile(r"^mcts_node_(\d+)_(\d+)\.json$")


class Tree:
    """Read-only files under a directory or under a prefix of a zip archive."""

    def __init__(self, root: str | Path | None = None, zf: zipfile.ZipFile | None = None,
                 prefix: str = ""):
        self.root = Path(root) if root is not None else None
        self.zf = zf
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        self._names: list[str] | None = None

    @property
    def label(self) -> str:
        return self.prefix.rstrip("/") if self.zf is not None else str(self.root)

    def names(self) -> list[str]:
        if self._names is None:
            if self.zf is not None:
                n = len(self.prefix)
                self._names = sorted(x[n:] for x in self.zf.namelist()
                                     if x.startswith(self.prefix) and not x.endswith("/"))
            else:
                assert self.root is not None
                self._names = sorted(p.relative_to(self.root).as_posix()
                                     for p in self.root.rglob("*") if p.is_file())
        return self._names

    def exists(self, rel: str) -> bool:
        if self.zf is not None:
            try:
                self.zf.getinfo(self.prefix + rel)
                return True
            except KeyError:
                return False
        assert self.root is not None
        return (self.root / rel).is_file()

    def read(self, rel: str) -> bytes:
        if self.zf is not None:
            return self.zf.read(self.prefix + rel)
        assert self.root is not None
        return (self.root / rel).read_bytes()

    def sub(self, rel_dir: str) -> Tree:
        if self.zf is not None:
            return Tree(zf=self.zf, prefix=self.prefix + rel_dir)
        assert self.root is not None
        return Tree(root=self.root / rel_dir)

    def subdirs(self) -> list[str]:
        return sorted({n.split("/", 1)[0] for n in self.names() if "/" in n})


def _text(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252", errors="replace")


# --------------------------------------------------------------------------- metadata


def metadata_columns(meta: Any) -> set[str]:
    """Column names from AutoDiscovery-style dataset metadata: ``datasets[].columns.raw[]``
    (asta / ai2), ``datasets[].columns[]`` (DiscoveryBench) or ``data_desc.fields[]``
    (BLADE)."""
    cols: set[str] = set()
    if not isinstance(meta, dict):
        return cols
    for ds in meta.get("datasets", []) or []:
        c = ds.get("columns") if isinstance(ds, dict) else None
        if isinstance(c, dict):
            c = c.get("raw", [])
        for col in c or []:
            if isinstance(col, dict) and col.get("name"):
                cols.add(str(col["name"]))
            elif isinstance(col, str):
                cols.add(col)
    for fld in (meta.get("data_desc") or {}).get("fields", []) or []:
        if isinstance(fld, dict) and fld.get("column"):
            cols.add(str(fld["column"]))
    return cols


def load_metadata(path: str | Path) -> tuple[set[str], str, str]:
    """(columns, display path, sha256) of a dataset metadata JSON file."""
    p = Path(path)
    b = p.read_bytes()
    return metadata_columns(json.loads(_text(b))), p.name, sha256_bytes(b)


# --------------------------------------------------------------------------- AutoDiscovery


def _plan_text(plan: Any) -> str:
    if isinstance(plan, dict):
        return "\n".join(f"{k}: {plan[k]}" for k in ("objective", "steps", "deliverables")
                         if plan.get(k))
    return str(plan or "")


def _mean(belief: Any) -> float | None:
    if isinstance(belief, dict):
        v = belief.get("mean")
        return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None
    if isinstance(belief, int | float) and not isinstance(belief, bool):
        return float(belief)
    return None


def _ad_node(d: dict[str, Any], file: str, sha: str, hosted: bool,
             columns: set[str] | None, columns_source: str | None) -> Node:
    nid = str(d.get("experiment_id") if hosted else d.get("id"))
    if hosted and d.get("id_in_run") is not None:
        nid = f"{nid}"
    success = d.get("success") if not hosted else None
    review = d.get("review")
    node = Node(
        id=nid, success=success if isinstance(success, bool) else None,
        review_text=review if isinstance(review, str) else None,
        surprising=d.get("is_surprising") if hosted else d.get("surprising"),
        prior_mean=_mean(d.get("prior")), posterior_mean=_mean(d.get("posterior")),
        columns=columns, columns_source=columns_source,
        meta={"belief_change": d.get("belief_change"), "status": d.get("status")} if hosted
        else {"belief_change": d.get("belief_change")},
    )

    def add(name: str, kind: str, value: Any) -> None:
        if isinstance(value, str) and value.strip() and value.strip() != "N/A":
            node.fields.append(TextField(name, kind, value, file, sha, in_json=True))

    add("hypothesis", CONTEXT, d.get("hypothesis"))
    add("experiment_plan", CONTEXT, _plan_text(d.get("experiment_plan")))
    add("code", CODE, d.get("code"))
    add("code_output", EVIDENCE, d.get("code_output"))
    add("analysis", CLAIM, d.get("analysis"))
    # the reviewer's text restates results only when it passed the node
    if success is True or (hosted and str(d.get("status", "")).lower() in ("success", "completed")):
        add("review", CLAIM, review)
    return node


def _level(nid: str) -> int | None:
    m = re.match(r"^node_(\d+)_(\d+)$", nid or "")
    return int(m.group(1)) if m else None


def load_autodiscovery(path: str | Path, metadata: str | Path | None = None) -> Run:
    p = Path(path)
    run = Run(run=p.name if p.is_dir() else p.parent.name, format="autodiscovery")
    records: list[tuple[dict[str, Any], str, str]] = []
    hosted = False
    base = p if p.is_dir() else p.parent

    def read_file(f: Path, role: str) -> bytes:
        b = f.read_bytes()
        run.inputs.append((f.relative_to(base).as_posix(), sha256_bytes(b), role))
        return b

    if p.is_dir():
        node_files = sorted((f for f in p.glob("mcts_node_*.json") if _NODE_FILE.match(f.name)),
                            key=lambda f: tuple(int(x) for x in _NODE_FILE.match(f.name).groups()))
        if node_files:
            for f in node_files:
                b = read_file(f, "node")
                records.append((json.loads(_text(b)), f.name, sha256_bytes(b)))
        else:
            for name in ("mcts_nodes_all.json", "mcts_nodes.json", "results.json"):
                if (p / name).is_file():
                    p = p / name
                    break
            else:
                raise FileNotFoundError(f"no mcts_node_*.json, mcts_nodes_all.json, "
                                        f"mcts_nodes.json or results.json in {path}")
    if p.is_file():
        b = read_file(p, "nodes")
        data = json.loads(_text(b))
        sha = sha256_bytes(b)
        if isinstance(data, dict) and "experiments" in data:
            hosted = True
            records = [(e, p.name, sha) for e in data["experiments"]]
            run.run = str((data.get("run") or {}).get("run_id") or run.run)
        elif isinstance(data, list):
            records = [(e, p.name, sha) for e in data]
        else:
            raise ValueError(f"{p}: not a node list or a hosted results file")
    args: dict[str, Any] = {}
    if (base / "args.json").is_file():
        args = json.loads(_text(read_file(base / "args.json", "args")))
    columns: set[str] | None = None
    col_src = None
    meta_path: Path | None = Path(metadata) if metadata else None
    if meta_path is None and isinstance(args.get("dataset_metadata"), str):
        for cand in (Path(args["dataset_metadata"]), base / args["dataset_metadata"],
                     base / Path(args["dataset_metadata"]).name):
            if cand.is_file():
                meta_path = cand
                break
        if meta_path is None:
            run.notes.append(f"args.json names dataset_metadata {args['dataset_metadata']!r} "
                             "but it was not found; A3 not checked (pass --metadata)")
    if meta_path is not None:
        columns, name, sha = load_metadata(meta_path)
        col_src = f"{name} ({sha[:12]})"
        run.inputs.append((name, sha, "dataset_metadata"))
    elif not args:
        run.notes.append("no args.json and no --metadata: A3 not checked")
    skipped = []
    for d, file, sha in records:
        if not isinstance(d, dict):
            continue
        nid = str(d.get("experiment_id") if hosted else d.get("id"))
        lvl = _level(nid) if not hosted else None
        if (lvl is not None and lvl < 2) or not d.get("hypothesis"):
            skipped.append(nid)
            continue
        run.nodes.append(_ad_node(d, file, sha, hosted, columns, col_src))
    if skipped:
        run.notes.append(f"skipped {len(skipped)} nodes with no experiment (root or seed level, "
                         f"or no hypothesis): {', '.join(sorted(skipped)[:20])}")
    return run


# --------------------------------------------------------------------------- CodeScientist


def _cs_final_dir(t: Tree) -> str | None:
    mods = sorted({n.split("/", 1)[0] for n in t.names() if n.startswith("modal-python-")})
    with_res = [m for m in mods if t.exists(f"{m}/modal-output/results.json")]
    return (with_res or mods or [None])[-1]


def is_codescientist_experiment(t: Tree) -> bool:
    return t.exists("history.json") or any(n.startswith("modal-python-") for n in t.names())


def load_codescientist_experiment(t: Tree, node_id: str | None = None,
                                  reruns: list[str] | None = None,
                                  rerun_source: str | None = None,
                                  inputs: list[tuple[str, str, str]] | None = None) -> Node:
    nid = node_id or t.label.rstrip("/").split("/")[-1]
    node = Node(id=nid, reruns=reruns, rerun_source=rerun_source)
    def field(name: str, kind: str, rel: str, in_json: bool = False,
              text: str | None = None) -> TextField | None:
        if not t.exists(rel):
            return None
        b = t.read(rel)
        sha = sha256_bytes(b)
        if inputs is not None:
            inputs.append((f"{nid}/{rel}", sha, name))
        f = TextField(name, kind, _text(b) if text is None else text, rel, sha,
                      in_json=in_json)
        node.fields.append(f)
        return f

    history: dict[str, Any] = {}
    if t.exists("history.json"):
        try:
            history = json.loads(_text(t.read("history.json"))).get("metadata", {}) or {}
        except (ValueError, AttributeError):
            history = {}
    final = _cs_final_dir(t)
    if final is not None:
        field("code", CODE, f"{final}/main.py")
        field("stdout", EVIDENCE, f"{final}/modal-output/stdout.python.txt")
        field("log", EVIDENCE, f"{final}/modal-output/log.json")
        rf = field("results", EVIDENCE, f"{final}/modal-output/results.json")
        if rf is not None:
            try:
                node.results = json.loads(rf.text) if rf.text.strip() else None
            except ValueError:
                node.results = None
        node.meta["final_run"] = final
    report = None
    for rel in ("report/report.tex", "report-watermarked/report.tex"):
        if t.exists(rel):
            report = field("report", CLAIM, rel)
            break
    if report is not None:
        report.mask = latex_mask(report.text)
        node.meta["claim_source"] = report.file
        ab = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", report.text, re.S)
        if ab:
            node.meta["headline"] = ["report", ab.start(1), ab.end(1)]
    else:
        summ = history.get("summary") or (history.get("summary_results") or {}).get("summary")
        if isinstance(summ, str) and summ.strip() and t.exists("history.json"):
            b = t.read("history.json")
            node.fields.append(TextField("summary", CLAIM, summ, "history.json",
                                         sha256_bytes(b), in_json=True))
            node.meta["claim_source"] = "history.json#summary"
    # CodeScientist has no "surprising" field: every reported experiment is a candidate
    # finding. The system's own interesting_results flag is kept as metadata only.
    ir = history.get("interesting_results")
    node.meta["interesting_results"] = bool(ir) if isinstance(ir, bool | int) else None
    node.surprising = None
    pm = history.get("current_pilot_mode")
    if not pm and isinstance(node.results, dict):
        pm = node.results.get("pilot_mode") or node.results.get("mode")
    node.pilot_mode = str(pm) if pm else None
    if final is None:
        node.uncheckable = "no modal-python-* run directory"
    return node


_LATEX_MASKS = [
    re.compile(r"\\(?:includegraphics|label|ref|eqref|cite[tp]?|vspace|hspace|setlength|"
               r"usepackage|documentclass|input|include|bibliography\w*|resizebox|scalebox|"
               r"addtolength|definecolor|url|href)\*?\s*(?:\[[^\]]*\])?(?:\{[^}]*\}){0,3}"),
    re.compile(r"\\begin\{(?:tabular|tabularx|longtable|array)\}(?:\[[^\]]*\])?\{[^}]*\}"),
    re.compile(r"\\begin\{(?:figure|table)\}\[[^\]]*\]"),
    re.compile(r"\\(?:begin|end)\{[^}]*\}"),
    re.compile(r"\\[a-zA-Z]+\[[^\]]*\]"),
    re.compile(r"(?m)(?<!\\)%.*$"),
]


def latex_mask(text: str) -> list[tuple[int, int]]:
    """Spans of a LaTeX report that are layout, not claims: the preamble, figure and
    table options, labels, references and comments."""
    spans: list[tuple[int, int]] = []
    m = re.search(r"\\begin\{document\}", text)
    if m:
        spans.append((0, m.end()))
    for rx in _LATEX_MASKS:
        spans.extend((x.start(), x.end()) for x in rx.finditer(text))
    return sorted(spans)


def load_codescientist(path: str | Path | Tree, reruns: dict[str, list[str]] | None = None
                       ) -> Run:
    t = path if isinstance(path, Tree) else Tree(root=path)
    run = Run(run=t.label.rstrip("/").split("/")[-1], format="codescientist")
    if is_codescientist_experiment(t):
        exps: Iterable[tuple[str, Tree]] = [(run.run, t)]
    else:
        exps = [(d, t.sub(d)) for d in t.subdirs() if is_codescientist_experiment(t.sub(d))]
    for name, sub in exps:
        rr = (reruns or {}).get(name)
        node = load_codescientist_experiment(sub, node_id=name, reruns=rr,
                                             rerun_source="supplied" if rr else None,
                                             inputs=run.inputs)
        if not is_codescientist_experiment(t):
            for f in node.fields:
                f.file = f"{name}/{f.file}"
        run.nodes.append(node)
    if not run.nodes:
        raise FileNotFoundError(f"no CodeScientist experiment directory in {t.label}")
    return run


def detect_format(path: str | Path) -> str:
    p = Path(path)
    if p.is_file():
        try:
            data = json.loads(_text(p.read_bytes()))
        except ValueError as exc:
            raise ValueError(f"{p}: not JSON") from exc
        if isinstance(data, list) or (isinstance(data, dict) and "experiments" in data):
            return "autodiscovery"
        raise ValueError(f"{p}: cannot tell the format")
    if any(p.glob("mcts_node_*.json")) or (p / "mcts_nodes_all.json").is_file() or \
            (p / "mcts_nodes.json").is_file():
        return "autodiscovery"
    if (p / "results.json").is_file():
        try:
            data = json.loads(_text((p / "results.json").read_bytes()))
            if isinstance(data, dict) and "experiments" in data:
                return "autodiscovery"
        except ValueError:
            pass
    t = Tree(root=p)
    if is_codescientist_experiment(t) or any(is_codescientist_experiment(t.sub(d))
                                             for d in t.subdirs()):
        return "codescientist"
    raise ValueError(f"{p}: neither an AutoDiscovery output nor a CodeScientist experiment; "
                     "pass --format")
