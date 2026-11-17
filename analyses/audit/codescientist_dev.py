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


def run() -> tuple[list[dict], dict]:
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
            "reruns": reruns,
        })
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
    return ms, {"rows": rows}


def table_md(info: dict) -> str:
    lines = [
        "# Development set: the audit on CodeScientist Table 4",
        "",
        "Generated by `analyses/audit/run_all.py`; do not edit. DEV set: the rules were "
        "written knowing these reasons. Codes are the audit codes with severity error or "
        "warning on the experiment; `intended` are the codes meant for the human reason.",
        "",
        "| # | idea | human | reason | audit verdict | codes | intended | caught |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in info["rows"]:
        lines.append(
            f"| {r['table4']} | {r['idea']} | {r['human']} | "
            f"{REASON_TEXT.get(r['reason'] or '', '')} | {r['verdict']} | "
            f"{' '.join(r['codes']) or '-'} | {' '.join(r['intended']) or '-'} | "
            f"{' '.join(r['caught_by']) or ('-' if r['human'] == 'accepted' else 'no')} |")
    return "\n".join(lines) + "\n"
