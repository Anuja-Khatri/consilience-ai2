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

Caveat, stated with every number: the synthetic generator builds columns from a semantic
tree, so a distractor can be genuinely associated with the target. A distractor hit is a
"discovery outside the gold relation", not necessarily a false one. The permuted-target
control (the target shuffled with a fixed seed per task) is where every hit is false by
construction.
"""

from __future__ import annotations

from collections import Counter

from consilience_ai2.audit.discoverybench import permuted_target, read_csv, scan_task, tasks
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
    return ms, info
