"""DEV: the audit against the 19 human verdicts in the CodeScientist paper (Table 4).

This is a development set, not a test. The rejection reasons are public and the audit's
rules were written knowing them, so these numbers say how the rules behave on the cases
that motivated them, not how they generalise.

Table 4 of the CodeScientist paper (arXiv 2503.22708) lists 19 candidate discoveries: 6
accepted by external and internal review and 13 rejected, each rejected one with the
internal reviewer's reason. The 20 experiment directories in the
``codescientist-example-experiments`` archive are those discoveries plus one
(``basicknowledgesharing``) that is not in Table 4; the mapping below was made by idea
name and checked against the external-review soundness and novelty averages, which match
Table 4 for 18 of the 19 (``simplemetaphorgraph``'s novelty average differs in the
released ratings file). The reasons are paraphrased; each reason category names the audit
codes meant to catch it.

R2 needs reruns: each discovery's idea was run five times in the full50 batch, and the
meta-analysis file in the repository labels each completed run support, refute or
inconclusive. Those labels are supplied to R2 as data.

Two rule versions are reported side by side. ``audit.dev.*`` (and ``audit.dev.v1.*``) are
rules v0.1 (``audit-rules-1``), recomputed from the frozen v0.1 rules taken from git
(``rules_versions.run_under``), so they never change when the rules do. ``audit.dev.v2.*``
are rules v0.2 (``audit-rules-2``, the working copy). Both are labelled dev: the v0.2
recalibration was decided on principle, but by people who had seen these 19 cases.
"""

from __future__ import annotations

from collections import Counter

from codescientist_common import (
    EXAMPLES_PREFIX,
    audit_dir,
    error_flagged,
    example_dirs,
    examples_zip,
    flagged_codes,
    idea_of_dir,
    judgements,
)
from rules_versions import V01, run_under

from consilience_ai2.core.results import metric

SOURCE = "fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis)"

# (Table 4 number, idea, human verdict, reason category)
TABLE4 = [
    (1, "simulationconfidenceanalysis", "accepted", None),
    (2, "progressivestatecomplexity", "accepted", None),
    (3, "twostagegamegeneration", "accepted", None),
    (4, "resistorsubstitutionadvisor", "accepted", None),
    (5, "basicconfidencesimulation", "accepted", None),
    (6, "knowledgegraphdiscovery", "accepted", None),
    (7, "simplesocialgraphs", "rejected", "few_samples_unvalidated_metric"),
    (8, "simpleplanningagent", "rejected", "effect_vanished_at_scale"),
    (9, "locationgraphcooking", "rejected", "effect_vanished_at_scale"),
    (10, "actionoutcometracking", "rejected", "effect_vanished_at_scale"),
    (11, "simpletemplatediscovery", "rejected", "partly_hardcoded_agent"),
    (12, "llmgraphverification", "rejected", "built_but_unused"),
    (13, "simpleaffordanceexploration", "rejected", "random_only_baseline"),
    (14, "wordnetcookingexploration", "rejected", "random_only_baseline"),
    (15, "simplemetaphorgraph", "rejected", "unclear_motivation"),
    (16, "simplegoalexplorer", "rejected", "random_only_baseline"),
    (17, "cookinggraphexplorer", "rejected", "random_only_baseline"),
    (18, "templateworldgeneration", "rejected", "foregone_conclusion_hardcoded"),
    (19, "simplegraphalignment", "rejected", "report_lacks_details"),
]

# Which codes each reason category is meant to be caught by ("intended").
INTENDED = {
    "random_only_baseline": ("R1",),
    "effect_vanished_at_scale": ("R2", "R3", "A6"),
    "few_samples_unvalidated_metric": ("R3", "A2"),
    "partly_hardcoded_agent": ("R4",),
    "built_but_unused": ("R5",),
    "foregone_conclusion_hardcoded": ("R4",),
    "report_lacks_details": ("A2", "A4", "A7"),
    "unclear_motivation": (),  # not a deterministic property; out of scope
}
REASON_TEXT = {
    "random_only_baseline": "baseline too simple (a random agent)",
    "effect_vanished_at_scale": "effect did not replicate with more samples",
    "few_samples_unvalidated_metric": "overly simple benchmark, few samples, judge metric not validated",
    "partly_hardcoded_agent": "agent partly hard-coded",
    "built_but_unused": "the agents never use the graph they build",
    "foregone_conclusion_hardcoded": "both conditions hard-coded: a foregone conclusion",
    "report_lacks_details": "report lacks details to evaluate",
    "unclear_motivation": "unclear motivation and utility",
}


LEVELS = ("pass", "flag(warning)", "flag(error)", "refuse")


def level_of(row: dict) -> str:
    """The explicit verdict level. Rules v0.2 report it; for v0.1 it follows that version's
    mapping (refuse on U1, A1 or A3 errors; a flag with another error is flag(error))."""
    if row.get("verdict_level"):
        return row["verdict_level"]
    if row["verdict"] == "flag":
        return "flag(error)" if row["error_flag"] else "flag(warning)"
    return row["verdict"]


def evaluate() -> list[dict]:
    """Audit the 19 discoveries with the rules in the loaded package."""
    dirs = {idea_of_dir(d): d for d in example_dirs()}
    judg = judgements()
    rows = []
    for num, idea, verdict, reason in TABLE4:
        d = dirs[idea]
        reruns = sorted(judg.get(idea, {}).values()) or None
        node = audit_dir(examples_zip(), EXAMPLES_PREFIX, d, reruns=reruns)
        codes = flagged_codes(node)
        intended = INTENDED.get(reason or "", ())
        rows.append({
            "table4": num, "idea": idea, "dir": d, "human": verdict, "reason": reason,
            "verdict": node["verdict"], "codes": codes,
            "error_codes": flagged_codes(node, ("error",)),
            "error_flag": error_flagged(node), "any_flag": bool(codes),
            "intended": list(intended), "caught_by": sorted(set(codes) & set(intended)),
            "reruns": reruns, "verdict_level": node.get("verdict_level"),
            "notes": node.get("notes"),
        })
    for r in rows:
        if r["verdict_level"] is None:
            del r["verdict_level"], r["notes"]
    return rows


def rows_only() -> tuple[list[dict], dict]:
    """For ``run_under``: the per-discovery rows only."""
    return [], {"rows": evaluate()}


def metrics_v01(rows: list[dict]) -> list[dict]:
    """The rules v0.1 dev metrics, exactly as first published (ids ``audit.dev.*``)."""
    acc = [r for r in rows if r["human"] == "accepted"]
    rej = [r for r in rows if r["human"] == "rejected"]
    in_scope = [r for r in rej if INTENDED[r["reason"]]]
    cav = ["development set: the rejection reasons are public and the rules were written "
           "knowing them", "19 discoveries from CodeScientist Table 4"]
    ms = [
        metric("audit.dev.rejected_flagged_intended", sum(1 for r in rej if r["caught_by"]),
               n=len(rej), source=SOURCE, dev_or_heldout="dev", caveats=cav + [
                   "count of rejected discoveries flagged by a code meant for their reason; "
                   "one reason (unclear motivation) has no such code"],
               unit="discoveries"),
        metric("audit.dev.rejected_in_scope_flagged_intended",
               sum(1 for r in in_scope if r["caught_by"]), n=len(in_scope), source=SOURCE,
               dev_or_heldout="dev", caveats=cav + ["excludes the unclear-motivation rejection"],
               unit="discoveries"),
        metric("audit.dev.rejected_flagged_error", sum(1 for r in rej if r["error_flag"]),
               n=len(rej), source=SOURCE, dev_or_heldout="dev", caveats=cav,
               unit="discoveries", description="rejected discoveries with any error-severity code"),
        metric("audit.dev.rejected_flagged_any", sum(1 for r in rej if r["any_flag"]),
               n=len(rej), source=SOURCE, dev_or_heldout="dev", caveats=cav,
               unit="discoveries", description="rejected discoveries with any error or warning"),
        metric("audit.dev.accepted_flagged_error", sum(1 for r in acc if r["error_flag"]),
               n=len(acc), source=SOURCE, dev_or_heldout="dev", caveats=cav,
               unit="discoveries", description="false flags: accepted discoveries with any "
               "error-severity code"),
        metric("audit.dev.accepted_flagged_any", sum(1 for r in acc if r["any_flag"]),
               n=len(acc), source=SOURCE, dev_or_heldout="dev", caveats=cav,
               unit="discoveries", description="false flags: accepted discoveries with any "
               "error or warning"),
    ]
    for reason in INTENDED:
        grp = [r for r in rej if r["reason"] == reason]
        ms.append(metric(f"audit.dev.reason.{reason}.caught", sum(1 for r in grp if r["caught_by"]),
                         n=len(grp), source=SOURCE, dev_or_heldout="dev", caveats=cav,
                         unit="discoveries",
                         description=f"{REASON_TEXT[reason]}: flagged by "
                         f"{'/'.join(INTENDED[reason]) or 'no code (out of scope)'}"))
    code_rej = Counter(c for r in rej for c in r["codes"])
    code_acc = Counter(c for r in acc for c in r["codes"])
    for code in sorted(set(code_rej) | set(code_acc)):
        ms.append(metric(f"audit.dev.code.{code.lower()}.rejected", code_rej.get(code, 0),
                         n=len(rej), source=SOURCE, dev_or_heldout="dev", caveats=cav,
                         unit="discoveries"))
        ms.append(metric(f"audit.dev.code.{code.lower()}.accepted", code_acc.get(code, 0),
                         n=len(acc), source=SOURCE, dev_or_heldout="dev", caveats=cav,
                         unit="discoveries", description="false flags by this code"))
    return ms


def matrix(rows: list[dict], tag: str, version: str) -> list[dict]:
    """Confusion matrix: human verdict x audit verdict level (``audit.dev.<tag>.matrix.*``)."""
    cav = ["development set: the rejection reasons are public and the rules were written "
           "knowing them", f"rules {version}", "19 discoveries from CodeScientist Table 4"]
    out = []
    for human in ("accepted", "rejected"):
        grp = [r for r in rows if r["human"] == human]
        for lv in LEVELS:
            key = lv.replace("(", "_").replace(")", "")
            out.append(metric(f"audit.dev.{tag}.matrix.{human}.{key}",
                              sum(1 for r in grp if level_of(r) == lv), n=len(grp),
                              source=SOURCE, dev_or_heldout="dev", caveats=cav,
                              unit="discoveries",
                              description=f"{human} discoveries with verdict {lv}"))
    return out


def metrics_v02(rows: list[dict]) -> list[dict]:
    """Rules v0.2 dev metrics (ids ``audit.dev.v2.*``), parallel to the v0.1 ones."""
    cav = ["development set: the rejection reasons are public and the v0.2 recalibration was "
           "made by people who had seen them", "rules v0.2 (audit-rules-2)",
           "19 discoveries from CodeScientist Table 4"]
    acc = [r for r in rows if r["human"] == "accepted"]
    rej = [r for r in rows if r["human"] == "rejected"]
    in_scope = [r for r in rej if INTENDED[r["reason"]]]

    def m(mid, value, grp, desc):
        return metric(f"audit.dev.v2.{mid}", value, n=len(grp), source=SOURCE,
                      dev_or_heldout="dev", caveats=cav, unit="discoveries", description=desc)

    ms = [
        m("rejected_flagged_intended", sum(1 for r in rej if r["caught_by"]), rej,
          "rejected discoveries flagged (error or warning) by a code meant for their reason"),
        m("rejected_in_scope_flagged_intended", sum(1 for r in in_scope if r["caught_by"]),
          in_scope, "as above, without the unclear-motivation rejection"),
        m("rejected_flagged_error", sum(1 for r in rej if r["error_flag"]), rej,
          "rejected discoveries with any error-severity code"),
        m("rejected_flagged_any", sum(1 for r in rej if r["any_flag"]), rej,
          "rejected discoveries with any error or warning"),
        m("accepted_flagged_error", sum(1 for r in acc if r["error_flag"]), acc,
          "false flags: accepted discoveries with any error-severity code"),
        m("accepted_flagged_any", sum(1 for r in acc if r["any_flag"]), acc,
          "false flags: accepted discoveries with any error or warning"),
    ]
    for reason in INTENDED:
        grp = [r for r in rej if r["reason"] == reason]
        ms.append(m(f"reason.{reason}.caught", sum(1 for r in grp if r["caught_by"]), grp,
                    f"{REASON_TEXT[reason]}: flagged by "
                    f"{'/'.join(INTENDED[reason]) or 'no code (out of scope)'}"))
    code_rej = Counter(c for r in rej for c in r["codes"])
    code_acc = Counter(c for r in acc for c in r["codes"])
    code_err_acc = Counter(c for r in acc for c in r["error_codes"])
    for code in sorted(set(code_rej) | set(code_acc)):
        ms.append(m(f"code.{code.lower()}.rejected", code_rej.get(code, 0), rej,
                    "rejected discoveries flagged by this code"))
        ms.append(m(f"code.{code.lower()}.accepted", code_acc.get(code, 0), acc,
                    "false flags by this code (error or warning)"))
        ms.append(m(f"code.{code.lower()}.accepted_error", code_err_acc.get(code, 0), acc,
                    "false flags by this code at error severity"))
    a7 = sum(1 for r in rows if "A7" in (r.get("notes") or []))
    ms.append(m("notes.a7", a7, rows, "discoveries with an A7 info note (no effect size): a "
                "reporting convention, not a flag"))
    return ms + matrix(rows, "v2", "v0.2 (audit-rules-2)")


def discovery5_sd() -> tuple[list[dict], dict]:
    """The accepted discovery 5 reports "SD = 15.8%" for per-game accuracy, a number its run
    never printed (A1). Recomputed here from the final run's results.json: the share of
    steps whose ``llm_prediction`` equals ``actual_outcome``, per ``game_id``."""
    import json
    import statistics
    from collections import defaultdict

    d = {idea_of_dir(x): x for x in example_dirs()}["basicconfidencesimulation"]
    z = examples_zip()
    pre = f"{EXAMPLES_PREFIX}{d}/"
    runs = sorted({n[len(pre):].split("/", 1)[0] for n in z.namelist()
                   if n.startswith(pre + "modal-python-")})
    rows = json.loads(z.read(f"{pre}{runs[-1]}/modal-output/results.json"))
    games: dict = defaultdict(list)
    for r in rows:
        games[r["game_id"]].append(r["llm_prediction"] == r["actual_outcome"])
    acc = [sum(v) / len(v) for _, v in sorted(games.items())]
    cav = ["development set (accepted discovery 5)", "recomputed from the run's results.json; "
           "the report prints SD = 15.8%, which the run never printed"]
    src = "fetch:codescientist-example-experiments"
    ms = [metric("audit.dev.v2.discovery5.accuracy_sd_sample", round(statistics.stdev(acc), 4),
                 n=len(acc), source=src, dev_or_heldout="dev", caveats=cav, unit="games",
                 description="sample SD of per-game accuracy"),
          metric("audit.dev.v2.discovery5.accuracy_sd_population",
                 round(statistics.pstdev(acc), 4), n=len(acc), source=src,
                 dev_or_heldout="dev", caveats=cav, unit="games",
                 description="population SD of per-game accuracy")]
    return ms, {"run": runs[-1], "games": len(acc), "steps": len(rows)}


def run() -> tuple[list[dict], dict]:
    _, info01 = run_under(V01, "codescientist_dev", "rows_only")
    rows01 = info01["rows"]
    rows02 = evaluate()
    sd_ms, sd_info = discovery5_sd()
    ms = (metrics_v01(rows01) + matrix(rows01, "v1", "v0.1 (audit-rules-1)")
          + metrics_v02(rows02) + sd_ms)
    return ms, {"rows": rows01, "rows_v2": rows02, "discovery5_sd": sd_info}


def table_md(info: dict) -> str:
    v2 = {r["table4"]: r for r in info["rows_v2"]}
    lines = [
        "# Development set: the audit on CodeScientist Table 4",
        "",
        "Generated by `analyses/audit/run_all.py`; do not edit. DEV set, not blind: the rules "
        "were written knowing these reasons, and the v0.2 recalibration was made by people who "
        "had seen these cases. Codes are the audit codes with severity error or warning; "
        "codes at error severity are in bold. `intended` are the codes meant for the human "
        "reason; `caught` counts an intended code at error or warning severity.",
        "",
        "| # | idea | human | reason | v0.1 verdict | v0.1 codes | v0.2 verdict | v0.2 codes "
        "| intended | caught (v0.1 / v0.2) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    def codes(r):
        err = set(r["error_codes"])
        return " ".join(f"**{c}**" if c in err else c for c in r["codes"]) or "-"

    def caught(r):
        if r["human"] == "accepted":
            return "-"
        return " ".join(r["caught_by"]) or "no"

    for r in info["rows"]:
        r2 = v2[r["table4"]]
        lines.append(
            f"| {r['table4']} | {r['idea']} | {r['human']} | "
            f"{REASON_TEXT.get(r['reason'] or '', '')} | {level_of(r)} | {codes(r)} | "
            f"{level_of(r2)} | {codes(r2)} | {' '.join(r['intended']) or '-'} | "
            f"{caught(r)} / {caught(r2)} |")
    return "\n".join(lines) + "\n"
