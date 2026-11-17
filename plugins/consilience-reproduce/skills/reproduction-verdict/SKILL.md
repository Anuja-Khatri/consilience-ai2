---
name: reproduction-verdict
description: Reads a reproduction's verdict from its numbers, not its prose, on the three axes of the asta-flows Secondary reproduction workflow (faithfulness, decidability, outcome), and checks that the thresholds were committed before the result and the hypothesis was copied verbatim. Use when someone has re-tested a hypothesis on independent data, or is about to, and wants the verdict, or wants to know whether a test could decide at all.
allowed-tools: Bash(consilience-ai2 reproduce *) Bash(uv tool *) Bash(git log *) Bash(command -v *)
---

# Reproduction verdict

A reproduction is judged on three separate axes, as the asta-flows "Secondary
reproduction" workflow defines them:

- **Faithfulness.** Is the independent test the same quantity, a proxy, or a
  substitution? A proxy is a caveat carried with the verdict, never a verdict. A
  substitution is not a reproduction and is not run.
- **Decidability.** Could the test decide? If not, the verdict is **undecided**, with one
  reason: **underpowered**, **no data** or **not identifiable**.
- **Outcome**, for a test that could decide: **supported**, **partly supported**,
  **opposite effect** or **rejected** (a null with adequate power and a passing positive
  control).

"A favorable estimate that misses the threshold is undecided, not support. Read the
verdict from the numbers, not from the prose." This skill does exactly that, with code
rather than judgement.

## Setup

```bash
command -v consilience-ai2 || uv tool install "consilience-ai2[consilience] @ git+https://github.com/Anuja-Khatri/consilience-ai2"
```

The `consilience` extra adds unit conversion and typed condition comparison for the
faithfulness check. Without it the check still runs, comparing units by name.

## Plan and run

1. **Write one record per hypothesis** before running the test: the hypothesis copied
   verbatim from the source run, the source claim (quantity, value, unit, n, effect size
   and type, conditions), the declared quantity mapping (`same_quantity`, `proxy` or
   `substitution`), the independence axis (instrument, cohort, region, method or time),
   and the thresholds: `alpha`, and either `minimum_effect` or `equivalence_margin`.
   Commit it. The record format is the JSON Schema shipped with the package
   (`consilience_ai2/reproduce/data/reproduction_record.schema.json`); worked examples are
   in the repository's `examples/reproduce/records/`.
2. **Run the test**, then add the reproduction's numbers (effect, p, n, and se or ci for
   an equivalence margin) and the positive control's p. Commit again.
3. **Check it:**

   ```bash
   consilience-ai2 reproduce check reproduction/H1.yaml --repo .
   ```

   It writes `reproduction_verdict.json` beside the record and prints one annotation per
   check. For a whole run, the drop-in `verdict.py` (in the repository's
   `examples/reproduce/`) checks every record and writes the REPRODUCED / NOT
   REPRODUCED / UNDECIDED block of the workflow's mission statement from the numbers.

## Reading the result

| Code | What it says |
|---|---|
| F1 | `same_quantity`, `proxy` (a caveat), `substitution`, or `not_comparable(<what>)`: a unit, a condition other than the independence axis, the effect type or an unreadable number |
| D1 | `decidable`, `underpowered` (power at the source effect with the reproduction's n, below 0.8 by default), `no_data`, `not_identifiable`, or `uncheckable` (power cannot be computed) |
| V1 | `reproduced`, `not_reproduced` or `inconclusive`, with the rubric outcome beside it; warns when a `reported_verdict` written in prose disagrees |
| P1 | `committed_first`, or `thresholds_post_hoc` with a reason (an error when proven from git, a warning when it cannot be shown) |
| P2 | `verbatim` or `reworded` (after a fixed whitespace and quote normalisation) |

Exit code 1 means a defect in the record or the process (S1, F1 substitution or not
comparable, P1 proven post hoc, P2 reworded). The verdict itself never changes the exit
code: `not_reproduced` is a result, not a failure. Report what the tool says, including
an undecided verdict; do not upgrade it from the prose.
