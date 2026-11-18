"""A5 on the DiscoveryBench synthetic tasks: how many "discoveries" a fixed scan makes
among columns outside the gold relation, with and without Benjamini-Hochberg.

Tasks: all 903 synthetic queries (train 551, dev 153, test 200 metadata files minus a
stray notebook checkpoint copy, which the glob does not match). Only queries with a
machine-readable gold relation (``target_col`` and ``relevant_cols`` in the metadata) are
scanned; the others carry only a natural-language hypothesis, and turning that into a
target column and a set of gold columns would need the language matching this audit does
not do. Exclusions are counted by reason.

For each scanned task every column is tested against the target (tests per type in
``consilience_ai2.audit.discoverybench``) and BH runs within the task. A column is gold
when it is in ``relevant_cols`` (the target excepted) and a distractor otherwise.

Derived set (rules v0.2). The queries without a machine-readable gold relation are scanned
too, with a target and gold columns derived by a fixed rule
(``consilience_ai2.audit.discoverybench.derive_gold``: exact, whole-word matches of the
normalised column names in the question and gold hypothesis; target = first column named
in the question). Their metrics are ``audit.discoverybench.derived.*``, kept apart from the
machine-readable set; ``audit.discoverybench.derived.agreement.*`` applies the same rule to
the machine-readable queries and compares it with their gold relation.

Caveat, stated with every number: the synthetic generator builds columns from a semantic
tree, so a distractor can be genuinely associated with the target. A distractor hit is a
"discovery outside the gold relation", not necessarily a false one. The permuted-target
control (the target shuffled with a fixed seed per task) is where every hit is false by
construction.
"""

from __future__ import annotations

from collections import Counter

from consilience_ai2.audit.discoverybench import (
    derive_gold,
    permuted_target,
    read_csv,
    scan_task,
    tasks,
    with_derived_gold,
)
from consilience_ai2.core.results import metric
from consilience_ai2.fetch import require

SOURCE = "fetch:discoverybench"
SEED = 20261117
ALPHA = 0.05


def run() -> tuple[list[dict], dict]:
    root = require("discoverybench")
    all_tasks = tasks(root)
    excluded: Counter = Counter()
    cache: dict = {}
    d_n = d_raw = d_bh = 0
    g_n = g_raw = g_bh = 0
    t_raw = t_bh = 0
    p_n = p_raw = p_bh = p_task_raw = p_task_bh = 0
    tests_by_type: Counter = Counter()
    skipped: Counter = Counter()
    scanned = 0
    for i, t in enumerate(all_tasks):
        if not t.has_structured_gold:
            excluded["no machine-readable gold relation (target_col, relevant_cols)"] += 1
            continue
        if t.csv_path not in cache:
            cache[t.csv_path] = read_csv(t.csv_path)
        data = cache[t.csv_path]
        sc = scan_task(t, data)
        if sc.excluded:
            excluded[sc.excluded] += 1
            continue
        scanned += 1
        any_raw = any_bh = False
        for x in sc.tests:
            if x.p is None:
                skipped[x.skipped] += 1
                continue
            tests_by_type[x.test] += 1
            if x.kind == "distractor":
                d_n += 1
                d_raw += x.p < ALPHA
                d_bh += x.q < ALPHA
                any_raw |= x.p < ALPHA
                any_bh |= x.q < ALPHA
            else:
                g_n += 1
                g_raw += x.p < ALPHA
                g_bh += x.q < ALPHA
        t_raw += any_raw
        t_bh += any_bh
        # null control: the same scan against the target shuffled (seed fixed per task)
        null = scan_task(t, data, target_values=permuted_target(data[t.target], SEED + i))
        nr = [x for x in null.tests if x.p is not None]
        p_n += len(nr)
        hits_raw = sum(x.p < ALPHA for x in nr)
        hits_bh = sum(x.q < ALPHA for x in nr)
        p_raw += hits_raw
        p_bh += hits_bh
        p_task_raw += hits_raw > 0
        p_task_bh += hits_bh > 0
    cav = ["synthetic DiscoveryBench tasks; only tasks with target_col and relevant_cols",
           "distractors can be genuinely associated with the target (semantic-tree "
           "generation): a distractor hit is outside the gold relation, not necessarily false"]
    test = ("per column vs target: Spearman (numeric), point-biserial (binary-numeric), "
            "Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within "
            "task; alpha 0.05")
    ms = [
        metric("audit.discoverybench.tasks_total", len(all_tasks), n=len(all_tasks),
               source=SOURCE, dev_or_heldout="descriptive", caveats=[], unit="tasks"),
        metric("audit.discoverybench.tasks_scanned", scanned, n=len(all_tasks), source=SOURCE,
               dev_or_heldout="descriptive", unit="tasks",
               caveats=[f"{k}: {v}" for k, v in sorted(excluded.items())]),
        metric("audit.discoverybench.distractor_tests", d_n, n=scanned, source=SOURCE,
               dev_or_heldout="descriptive", caveats=cav, unit="column tests"),
        metric("audit.discoverybench.distractor_hit_rate_raw", round(d_raw / d_n, 4), n=d_n,
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav, test=test,
               description=f"distractor columns with raw p < {ALPHA} ({d_raw})"),
        metric("audit.discoverybench.distractor_hit_rate_bh", round(d_bh / d_n, 4), n=d_n,
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav, test=test,
               description=f"distractor columns with BH q < {ALPHA} ({d_bh})"),
        metric("audit.discoverybench.distractor_hits_raw", d_raw, n=d_n, source=SOURCE,
               dev_or_heldout="descriptive", caveats=cav, unit="column tests"),
        metric("audit.discoverybench.distractor_hits_bh", d_bh, n=d_n, source=SOURCE,
               dev_or_heldout="descriptive", caveats=cav, unit="column tests"),
        metric("audit.discoverybench.distractor_hit_reduction", round(1 - d_bh / d_raw, 4),
               n=d_raw, source=SOURCE, dev_or_heldout="descriptive", caveats=cav,
               description="1 - (BH hits / raw hits) among distractor columns"),
        metric("audit.discoverybench.tasks_with_distractor_hit_raw", round(t_raw / scanned, 4),
               n=scanned, source=SOURCE, dev_or_heldout="descriptive", caveats=cav),
        metric("audit.discoverybench.tasks_with_distractor_hit_bh", round(t_bh / scanned, 4),
               n=scanned, source=SOURCE, dev_or_heldout="descriptive", caveats=cav),
        metric("audit.discoverybench.gold_recall_raw", round(g_raw / g_n, 4), n=g_n,
               source=SOURCE, dev_or_heldout="descriptive", test=test, caveats=cav + [
                   "gold columns enter the target through nonlinear and conditional formulas; "
                   "a marginal test can miss them"]),
        metric("audit.discoverybench.gold_recall_bh", round(g_bh / g_n, 4), n=g_n,
               source=SOURCE, dev_or_heldout="descriptive", test=test, caveats=cav + [
                   "gold columns enter the target through nonlinear and conditional formulas; "
                   "a marginal test can miss them"]),
        metric("audit.discoverybench.null_hit_rate_raw", round(p_raw / p_n, 4), n=p_n,
               source=SOURCE, dev_or_heldout="synthetic", test=test + f"; target permuted, "
               f"numpy default_rng(seed {SEED} + task index)",
               caveats=["permuted-target control: every hit is false by construction"]),
        metric("audit.discoverybench.null_hit_rate_bh", round(p_bh / p_n, 4), n=p_n,
               source=SOURCE, dev_or_heldout="synthetic", test=test + f"; target permuted, "
               f"numpy default_rng(seed {SEED} + task index)",
               caveats=["permuted-target control: every hit is false by construction"]),
        metric("audit.discoverybench.null_tasks_any_hit_raw", round(p_task_raw / scanned, 4),
               n=scanned, source=SOURCE, dev_or_heldout="synthetic",
               caveats=["permuted-target control: share of tasks with at least one false "
                        "discovery"]),
        metric("audit.discoverybench.null_tasks_any_hit_bh", round(p_task_bh / scanned, 4),
               n=scanned, source=SOURCE, dev_or_heldout="synthetic",
               caveats=["permuted-target control: share of tasks with at least one false "
                        "discovery"]),
    ]
    info = {"excluded": dict(sorted(excluded.items())), "tests_by_type": dict(sorted(tests_by_type.items())),
            "skipped": dict(sorted((str(k), v) for k, v in skipped.items()))}
    dms, dinfo = derived(all_tasks, cache, scanned, test)
    info["derived"] = dinfo
    return ms + dms, info


def _scan_counts(sc) -> dict:
    c = {"d_n": 0, "d_raw": 0, "d_bh": 0, "g_n": 0, "g_raw": 0, "g_bh": 0, "any_raw": False,
         "any_bh": False}
    for x in sc.tests:
        if x.p is None:
            continue
        if x.kind == "distractor":
            c["d_n"] += 1
            c["d_raw"] += x.p < ALPHA
            c["d_bh"] += x.q < ALPHA
            c["any_raw"] |= x.p < ALPHA
            c["any_bh"] |= x.q < ALPHA
        else:
            c["g_n"] += 1
            c["g_raw"] += x.p < ALPHA
            c["g_bh"] += x.q < ALPHA
    return c


def derived(all_tasks, cache: dict, scanned_machine: int, test: str) -> tuple[list[dict], dict]:
    """The A5 scan on queries without a machine-readable gold relation, with the derived
    target and gold columns; plus the rule's agreement with the machine-readable gold."""
    rule = ("derived gold: whole-word matches of normalised column names in the question and "
            "gold hypothesis; target = first column named in the question (else hypothesis)")
    # agreement where both exist
    n_struct = n_usable = t_agree = inter = n_der = n_gold = 0
    for t in all_tasks:
        if not t.has_structured_gold:
            continue
        n_struct += 1
        dg = derive_gold(t)
        if not dg.usable:
            continue
        n_usable += 1
        t_agree += dg.target == t.target
        der = {dg.target, *dg.relevant}
        gold = set(t.relevant) | {t.target}
        inter += len(der & gold)
        n_der += len(der)
        n_gold += len(gold)
    excluded: Counter = Counter()
    tot = Counter()
    scanned = t_raw = t_bh = 0
    p_n = p_raw = p_bh = p_task_raw = p_task_bh = 0
    for i, t in enumerate(all_tasks):
        if t.has_structured_gold:
            continue
        dg = derive_gold(t)
        if not dg.usable:
            excluded["derived rule names no target and gold column"] += 1
            continue
        if t.csv_path not in cache:
            cache[t.csv_path] = read_csv(t.csv_path)
        data = cache[t.csv_path]
        td = with_derived_gold(t, dg)
        sc = scan_task(td, data)
        if sc.excluded:
            excluded[sc.excluded] += 1
            continue
        scanned += 1
        c = _scan_counts(sc)
        for k in ("d_n", "d_raw", "d_bh", "g_n", "g_raw", "g_bh"):
            tot[k] += c[k]
        t_raw += c["any_raw"]
        t_bh += c["any_bh"]
        null = scan_task(td, data, target_values=permuted_target(data[td.target], SEED + i))
        nr = [x for x in null.tests if x.p is not None]
        p_n += len(nr)
        hr = sum(x.p < ALPHA for x in nr)
        hb = sum(x.q < ALPHA for x in nr)
        p_raw += hr
        p_bh += hb
        p_task_raw += hr > 0
        p_task_bh += hb > 0
    n_nl = sum(1 for t in all_tasks if not t.has_structured_gold)
    cav = ["DERIVED set, kept apart from the machine-readable set: target and gold columns "
           "come from a lexical rule, not from the benchmark's gold relation", rule,
           "synthetic DiscoveryBench tasks; distractors can be genuinely associated with the "
           "target, and a derived target can be wrong (see the agreement metrics)"]
    acav = ["the derived rule applied to the queries that also have a machine-readable gold "
            "relation", rule]
    pre = "audit.discoverybench.derived"

    def r4(a, b):
        return round(a / b, 4) if b else None

    ms = [
        metric(f"{pre}.agreement.usable", n_usable, n=n_struct, source=SOURCE,
               dev_or_heldout="descriptive", caveats=acav, unit="tasks",
               description="machine-readable queries for which the rule derives a target and "
               "at least one gold column"),
        metric(f"{pre}.agreement.target", r4(t_agree, n_usable), n=n_usable, source=SOURCE,
               dev_or_heldout="descriptive", caveats=acav,
               description=f"derived target equals target_col ({t_agree})"),
        metric(f"{pre}.agreement.column_precision", r4(inter, n_der), n=n_der, source=SOURCE,
               dev_or_heldout="descriptive", caveats=acav,
               description="pooled share of derived relation columns (target and gold) that "
               "are in the machine-readable relation (relevant_cols and target_col)"),
        metric(f"{pre}.agreement.column_recall", r4(inter, n_gold), n=n_gold, source=SOURCE,
               dev_or_heldout="descriptive", caveats=acav,
               description="pooled share of machine-readable relation columns that the rule "
               "also derives"),
        metric(f"{pre}.tasks_without_machine_gold", n_nl, n=len(all_tasks), source=SOURCE,
               dev_or_heldout="descriptive", caveats=[], unit="tasks"),
        metric(f"{pre}.tasks_scanned", scanned, n=n_nl, source=SOURCE,
               dev_or_heldout="descriptive", unit="tasks",
               caveats=cav[:2] + [f"{k}: {v}" for k, v in sorted(excluded.items())]),
        metric("audit.discoverybench.coverage_machine", r4(scanned_machine, len(all_tasks)),
               n=len(all_tasks), source=SOURCE, dev_or_heldout="descriptive", caveats=[
                   "share of the synthetic queries scanned with a machine-readable gold "
                   "relation"]),
        metric("audit.discoverybench.coverage_machine_or_derived",
               r4(scanned_machine + scanned, len(all_tasks)), n=len(all_tasks), source=SOURCE,
               dev_or_heldout="descriptive", caveats=[
                   "share of the synthetic queries scanned with a machine-readable or a "
                   "derived gold relation", rule]),
        metric(f"{pre}.distractor_tests", tot["d_n"], n=scanned, source=SOURCE,
               dev_or_heldout="descriptive", caveats=cav, unit="column tests"),
        metric(f"{pre}.distractor_hit_rate_raw", r4(tot["d_raw"], tot["d_n"]), n=tot["d_n"],
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav, test=test,
               description=f"distractor columns with raw p < {ALPHA} ({tot['d_raw']})"),
        metric(f"{pre}.distractor_hit_rate_bh", r4(tot["d_bh"], tot["d_n"]), n=tot["d_n"],
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav, test=test,
               description=f"distractor columns with BH q < {ALPHA} ({tot['d_bh']})"),
        metric(f"{pre}.distractor_hit_reduction",
               round(1 - tot["d_bh"] / tot["d_raw"], 4) if tot["d_raw"] else None,
               n=tot["d_raw"], source=SOURCE, dev_or_heldout="descriptive", caveats=cav,
               description="1 - (BH hits / raw hits) among distractor columns"),
        metric(f"{pre}.tasks_with_distractor_hit_raw", r4(t_raw, scanned), n=scanned,
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav),
        metric(f"{pre}.tasks_with_distractor_hit_bh", r4(t_bh, scanned), n=scanned,
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav),
        metric(f"{pre}.gold_recall_raw", r4(tot["g_raw"], tot["g_n"]), n=tot["g_n"],
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav, test=test),
        metric(f"{pre}.gold_recall_bh", r4(tot["g_bh"], tot["g_n"]), n=tot["g_n"],
               source=SOURCE, dev_or_heldout="descriptive", caveats=cav, test=test),
        metric(f"{pre}.null_hit_rate_raw", r4(p_raw, p_n), n=p_n, source=SOURCE,
               dev_or_heldout="synthetic", test=test + f"; target permuted, numpy "
               f"default_rng(seed {SEED} + task index)",
               caveats=["permuted-target control on the derived set: every hit is false by "
                        "construction", rule]),
        metric(f"{pre}.null_hit_rate_bh", r4(p_bh, p_n), n=p_n, source=SOURCE,
               dev_or_heldout="synthetic", test=test + f"; target permuted, numpy "
               f"default_rng(seed {SEED} + task index)",
               caveats=["permuted-target control on the derived set: every hit is false by "
                        "construction", rule]),
        metric(f"{pre}.null_tasks_any_hit_raw", r4(p_task_raw, scanned), n=scanned,
               source=SOURCE, dev_or_heldout="synthetic",
               caveats=["permuted-target control on the derived set: share of tasks with at "
                        "least one false discovery", rule]),
        metric(f"{pre}.null_tasks_any_hit_bh", r4(p_task_bh, scanned), n=scanned,
               source=SOURCE, dev_or_heldout="synthetic",
               caveats=["permuted-target control on the derived set: share of tasks with at "
                        "least one false discovery", rule]),
    ]
    info = {"excluded": dict(sorted(excluded.items())), "scanned": scanned,
            "agreement": {"machine_readable": n_struct, "usable": n_usable,
                          "target_agree": t_agree, "intersection": inter,
                          "derived_columns": n_der, "gold_columns": n_gold},
            "counts": dict(sorted(tot.items()))}
    return ms, info
