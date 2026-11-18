# Reproduction verdict (`consilience-ai2 reproduce`)

Component C3. It turns the verdict rubric of the asta-flows "Secondary reproduction"
workflow into deterministic code: the verdict is read from the numbers in a structured
record, against thresholds committed before the result, never from prose. No language
model is called; the same record gives byte-identical output.

Rubric source: `plugins/asta-flows/skills/run-workflow/workflows/secondary-reproduction.md`
in asta-plugins (pinned at commit a2dcade), section "Verdicts" and steps 1 and 4.

```bash
consilience-ai2 reproduce check record.yaml [--repo PATH] [--json OUT] [--backend auto|consilience|fallback] [--pack PACK] [--skip CODE]
```

Python: `consilience_ai2.reproduce.check_file(path, repo=...)` returns a `Report`;
`report.extra["verdict"]` holds the summary and `report.write(...)` writes
`reproduction_verdict.json`.

## Rubric mapping

Each line of the asta-flows wording, and where it lives in the code.

| asta-flows wording | Code | Outcome in the report |
|---|---|---|
| "**Faithfulness.** Is the independent test the same quantity, a proxy, or a substitution?" | F1 | `same_quantity`, `proxy`, `substitution` |
| "A proxy is a caveat carried with the verdict, never a verdict." | F1, V1 | F1 `proxy` (warning); V1 is computed and carries the caveat in `caveats` |
| "A substitution is not a reproduction and is not run." | F1, V1 | F1 `substitution` (error); V1 outcome `not_a_reproduction`, verdict `inconclusive` |
| (Consilience comparability, added) a named mismatch the declaration cannot cover | F1 | `not_comparable(<what>)` (error); V1 `undecided(not_comparable)` |
| "**Decidability.** Could the test decide? If not, the verdict is **undecided**, with one reason:" | D1, V1 | D1 class; V1 `undecided(<class>)` |
| "**underpowered**: it ran, but had too few cases to detect the source effect;" | D1 | `underpowered` (power at the source effect with the reproduction's n) |
| "**no data**: no independent data covered it;" | D1 | `no_data` |
| "**not identifiable**: the construct cannot isolate the claim, for example because it is true by construction." | D1 | `not_identifiable` (declared in the record, with its reason) |
| (added) power cannot be computed from what the record gives | D1 | `uncheckable` (a named reason); never guessed |
| "**supported**: the threshold was met in the hypothesized direction;" | V1 | `supported` -> `reproduced` |
| "**partly supported**: one committed component met it;" | V1 | `partly_supported` from `aggregate()` over one record per component -> `inconclusive` |
| "**opposite effect**: significant in the other direction, which is never support;" | V1 | `opposite_effect` -> `not_reproduced` |
| "**rejected**: a null with adequate power and a passing positive control." | V1 | `rejected` -> `not_reproduced`; a null without a passing positive control is `undecided(no_positive_control)` or `undecided(positive_control_failed)` |
| "A favorable estimate that misses the threshold is undecided, not support." | V1 | `undecided(misses_threshold)` |
| "Read the verdict from the numbers, not from the prose." | V1 | V1 reads only numbers; a `reported_verdict` written by the agent is compared afterwards and a disagreement is a warning |
| "Commit the test and its threshold, both significance and minimum effect, before running anything." | P1 | `committed_first`, or `thresholds_post_hoc(<reason>)` |
| "Copy its hypothesis text verbatim … Do not group, merge or reword." | P2 | `verbatim`, `reworded`, `uncheckable` |
| "Only independent data counts. The run's own dataset is never reused." | F1 | the declared `independence_axis` must differ; equal is `not_comparable(conditions.<axis>)`, reason `not_independent` |
| mission.md: "REPRODUCED / NOT REPRODUCED (opposite effect, or rejected) / UNDECIDED, with the reason" | V1 | the three-way `verdict`: `reproduced` / `not_reproduced` / `inconclusive` |

Two choices the rubric leaves open, made here and stated: `partly_supported` maps to
`inconclusive` (the mission's NOT REPRODUCED bin names only opposite effect and
rejected, and partial support is not full support); and `not_comparable` and
`uncheckable` are added as fail-closed outcomes so nothing is ever guessed.

## The record

YAML or JSON, version 1, defined by
`consilience_ai2/reproduce/data/reproduction_record.schema.json` (JSON Schema; the
loader validates against this file). Worked synthetic examples are in
`examples/reproduce/records/`.

| Field | What |
|---|---|
| `hypothesis`, `source_hypothesis` | the text as tested, and the source run's text (P2) |
| `source`, `reproduction` | `quantity`, `value`, `unit`, `n`, `effect_size: {type, value}` (types `r`, `d`, `dz`, `h`, or `proportions` with `p1`, `p2`), `p`, `ci` + `ci_level` or `se`, `conditions` (a mapping), `status` (`ran`, `no_data`, `not_run`) |
| `quantity_mapping` | `relation`: `same_quantity`, `proxy` or `substitution`, and a `note` |
| `independence_axis` | `instrument`, `cohort`, `region`, `method` or `time` |
| `thresholds` | `alpha`, `sides` (1 or 2, default 2), exactly one of `minimum_effect` (with `minimum_effect_scale`: `effect_size`, the default, or `value`) and `equivalence_margin` (in the source unit), `power` (D1 threshold, default 0.8), `committed: {commit, time}` |
| `result_committed` | `{commit, time}` of the result |
| `direction` | `positive` or `negative`; default: the sign of the source effect |
| `positive_control` | `p` (passes when below alpha) or `passed` |
| `identifiability` | `{identifiable: false, reason}` to declare a claim not identifiable |
| `reported_verdict` | the prose verdict, compared but never used |

Loading is in two stages. Structure (parse, duplicate keys refused, schema) failing is
`S1`, an error, and nothing else runs. Numbers are read fail-closed with
`core.numbers`: a string must hold exactly one number and nothing else; ambiguous
separators (`1,2`, `1.234,5`), a percent sign, extra text, NaN, infinity and booleans
are refused and reported by field. YAML timestamps stay text.

## Checks

### F1 faithfulness

Fail-closed, in this order of precedence: a declared `substitution`; then any mismatch
(`not_comparable`, all mismatches listed, the label names every target); then a declared
`proxy`; else `same_quantity`. A mismatch is:

- an unreadable number on either side;
- quantity names: with no mapping they must be equal after `core.normalise`; a declared
  `same_quantity` with different names is refused (declare a proxy instead);
- the effect-size type, when either side gives one;
- units: both stated when a value is given, and of the same kind;
- any condition other than the independence axis, stated on one side only or differing;
- the independence axis not stated on both sides, or equal on both.

Units and conditions are compared by the PyPI `consilience` package when it is
installed (`pip install consilience`, or the `[consilience]` extra): `consilience.compare` with the
two sides' units and conditions (and `conditions_pack` or `--pack`, a consilience
compare pack), whose named defects (`not_comparable`, `not_stated`, `unparseable`) become
F1 targets. It converts units through pint, compares quantity-valued conditions after
conversion, and refuses a condition string that starts with a number but has no known
unit. Without the package, a fallback compares units by name (the dimensionless
spellings and `%`/`percent` are the only conversions) and conditions by exact value,
text after `core.normalise`; a pack is refused. Each F1 finding names the backend
(`consilience <version>` or `fallback`). The same backend converts the reproduction's
value, interval and standard error into the source unit for V1.

### D1 decidability

| # | Condition | D1 |
|---|---|---|
| 1 | `reproduction.status` is `no_data` or `not_run`, or no result numbers, or n = 0 | `no_data` |
| 2 | `identifiability.identifiable` is false | `not_identifiable` |
| 3 | power cannot be computed (no alpha, no source effect size, a zero source effect, no reproduction n, a formula's own limit; in equivalence mode, no standard error) | `uncheckable` |
| 4 | power below `thresholds.power` | `underpowered` |
| 5 | otherwise | `decidable` |

Power, closed form, at the magnitude of the SOURCE effect with the REPRODUCTION's n;
`z_c`, `t_c` are critical values at `1 - alpha` (one-sided) or `1 - alpha/2`
(two-sided); `Phi` the normal CDF; groups default to `n1 = floor(n/2)`, `n2 = n - n1`
unless `effect_size.n_groups` is given.

| Type | Power | Test statistic (when p is absent) |
|---|---|---|
| `r` | `Phi(atanh(abs(r)) * sqrt(n - 3) - z_c)`, plus the other tail when two-sided | `t = r * sqrt(n - 2) / sqrt(1 - r^2)`, df n - 2 |
| `d` | noncentral t, df `n1 + n2 - 2`, ncp `abs(d) * sqrt(n1*n2/(n1 + n2))`, `P(T' > t_c)` (+ `P(T' < -t_c)`) | `t = d * sqrt(n1*n2/(n1 + n2))` |
| `dz` | noncentral t, df `n - 1`, ncp `abs(dz) * sqrt(n)` | `t = dz * sqrt(n)` |
| `h` (proportions) | `h = 2*asin(sqrt(p1)) - 2*asin(sqrt(p2))`; `Phi(abs(h) * sqrt(n1*n2/(n1 + n2)) - z_c)` (+ other tail) | `z = h * sqrt(n1*n2/(n1 + n2))` |
| equivalence | two one-sided tests at zero difference: `max(0, 2*Phi(M/se - z(1 - alpha)) - 1)` | (interval, below) |

The unit tests check these against standard reference values (for example d = 0.5 with
64 per group, two-sided alpha 0.05: power 0.8015).

### V1 verdict

Minimum-effect mode. `s` is the hypothesized sign, `e` the reproduction effect on the
committed scale (converted to the source unit on the value scale), `m` the minimum
effect, `sig` is `p < alpha` (p from the record, else computed from the effect size and
n with the statistic above; one-sided p is in the hypothesized direction).

| # | Condition | Outcome | Verdict |
|---|---|---|---|
| 1 | F1 `substitution` | `not_a_reproduction` | `inconclusive` |
| 2 | F1 `not_comparable` | `undecided(not_comparable)` | `inconclusive` |
| 3 | D1 not `decidable` | `undecided(<D1 class>)` | `inconclusive` |
| 4 | an unreadable threshold or positive control, no direction, no effect or no p | `undecided(<named>)` | `inconclusive` |
| 5 | `sig` and `s*e < 0` | `opposite_effect` | `not_reproduced` |
| 6 | `sig` and `s*e > 0` and `abs(e) >= m` | `supported` | `reproduced` |
| 7 | `s*e > 0` and exactly one of `sig`, `abs(e) >= m` | `undecided(misses_threshold)` | `inconclusive` |
| 8 | not `sig`, `s*e <= 0` or `abs(e) < m`, positive control passed | `rejected` | `not_reproduced` |
| 9 | as 8, no positive control | `undecided(no_positive_control)` | `inconclusive` |
| 10 | as 8, positive control failed | `undecided(positive_control_failed)` | `inconclusive` |
| 11 | `sig` and `e = 0` | `undecided(inconsistent_numbers)` | `inconclusive` |

Equivalence mode (a margin M around the source value S): the `1 - 2*alpha` interval of
the reproduction value, from `se`, or from `ci` at `ci_level` (default 0.95) converted
to a standard error and re-centred on the value. Rows 1 to 4 as above, then: the
interval inside `[S - M, S + M]` is `supported`; wholly outside and beyond zero on the
side opposite to S is `opposite_effect`; wholly outside otherwise is
`rejected` (reason `not_equivalent`); overlapping an edge is
`undecided(interval_overlaps_margin)`.

Positive control: its `p` below alpha passes; a `passed` flag is used only without a p,
and a flag that disagrees with the p is reported.

### P1 commit order

First by declared refs (`thresholds.committed.commit`, `result_committed.commit`) in the
repository (`--repo`, else the one holding the record): both must resolve; the
thresholds commit must be a strict ancestor of the result commit (graph order, not clock
time; committer and declared times are reported). Else by the record file's own history
(`git log -- <record>`): each committed version is parsed; the first commit whose
thresholds equal the current ones must come strictly before the first commit with a
result number, and no commit from the result onwards may hold other thresholds.

| Outcome | Severity |
|---|---|
| `committed_first` | info |
| `thresholds_post_hoc(same_commit)`, `(after_result)`, `(changed_after_result)` | error |
| `thresholds_post_hoc(not_shown)`: no repository, untracked record, a ref that does not resolve, unrelated histories, result or thresholds not committed | warning |
| `not_applicable`: the record has no result numbers yet | info |

A threshold not shown to come first is not credited: it is reported as post hoc, with
the reason `not_shown` so it is not confused with a proven one.

### P2 verbatim hypothesis

`hypothesis` against `source_hypothesis` after `core.normalise` (ligatures, safe NFKC,
straight quotes, line-break hyphens, invisible characters, whitespace; case counts).
`verbatim` (info), `reworded` (error, with the first differing offset), `uncheckable`
(warning, a text missing). The receipt carries the SHA-256 of the source text and the
normalisation version.

### Severities and exit code

Exit 1 on any error: S1, F1 `substitution` or `not_comparable`, P1 proven post hoc, P2
`reworded`. Warnings: F1 `proxy`, D1 not decidable, V1 when the prose verdict
disagrees, P1 `not_shown`, P2 `uncheckable`. The verdict itself never changes the exit
code. Exit 2 is a usage error (a missing file, an unavailable backend).

## Output

`reproduction_verdict.json` is the core report format (version 1: `tool`, `inputs`
with SHA-256, `findings` with receipts, `summary`) plus `record` (path, SHA-256, id),
`verdict` (`faithfulness`, `decidability`, `outcome`, `outcome_label`, `reason`,
`verdict`, `commit_order`, `hypothesis_copy`, `caveats`), `rubric` and
`checks_skipped`. Each finding's receipt is the record's SHA-256 and the field checked.

## Integration

- **CLI and API** as above.
- **Drop-in script** `examples/reproduce/verdict.py`, in the pattern of the exploration
  workflow's `check.py` and `runlog.py`: placed in a run's `scripts/`, it checks every
  `reproduction/*.yaml`, writes `reproduction/reproduction_verdict.json`, and writes
  `reproduction/mission_verdicts.txt`, the REPRODUCED / NOT REPRODUCED / UNDECIDED block
  of the workflow's `mission.md`, filled from the numbers.
- **Claude Code plugin** `plugins/consilience-reproduce` with the skill
  `reproduction-verdict`.

## Results

All numbers below render from `results/reproduce.json` (written by
`analyses/reproduce/run.py`). Fixed seeds; the F1 fallback backend is used so the
numbers do not depend on whether `consilience` is installed. Two versions are reported:
**v0.1**, the first release, under its original metric ids, and **v0.2**, which changes
coverage and parsing only (`*.v0_2.*` metric ids). The verdict code, thresholds and pairs
are the same in both. The v0.2 rule was preregistered in
`prereg/reproduce/cs_extraction_v0_2.md` before any v0.2 number existed; three flaws found
in it after one run, and before any number was committed, are corrected in
`prereg/reproduce/cs_extraction_v0_2_deviations.md`, and the rule as preregistered is
reported too (`reproduce.cs.v0_2.as_preregistered.*`).

### (a) CodeScientist reruns as reproductions (descriptive)

The full-50 batch with expert notes (the batch whose run outputs are released): 50
ideas, 5 runs each. 24 ideas have at least 2 completed runs, giving 65 (source,
reproduction) pairs: the first completed run is the source, each later one a
reproduction. Design in `analyses/reproduce/codescientist_reruns.py`; v0.2 parsers in
`analyses/reproduce/cs_extract.py`.

**What v0.2 changes.** v0.1 read one file per run, the final iteration's
`results.json`, and used its bootstrap comparison only when there was exactly one. v0.2
reads, in this order, `results.json` (unchanged, so every v0.1 reading stands),
`to_save/**/*.json` (files the run saved for its report), and bootstrap results printed in
`log.json` (as JSON or as a Python dict). It parses tolerantly (a BOM, cp1252, NaN tokens,
Python literals, trailing commas; nothing is executed). Several candidate comparisons are
resolved by the run's stated hypothesis, then its experiment plan: the candidate with the
largest share of its distinctive words in the text wins, and a tie is left undecided.
Undecided pairs stay `no_data`, and every comparison found in both runs is judged
separately (the per-comparison table below). A mean difference of exactly 0 is recorded as
a zero effect. Runs with no bootstrap block anywhere are classified instead of read.

Coverage, v0.1 to v0.2 (pairs whose two runs both give the primary comparison):

| | v0.1 | v0.2 |
|---|---|---|
| recoverable | 24 of 65 (36.92%, 95% CI 26.23% to 49.08%) | 30 of 65 (46.15%, 95% CI 34.59% to 58.15%) |
| no bootstrap block in `results.json` | 22 | (read further: below) |
| several candidates, no choice | 15 | 17 |
| unreadable `results.json` | 4 | 0 (the 3 files are empty, not malformed) |
| no test output in any final file | (not classified) | 14 |
| a p-value without an estimate or n | (not classified) | 4 |

Where the 41 v0.1 `no_data` pairs went: 5 of the 22 without a block in `results.json`
became recoverable (blocks in `to_save/` or `log.json`), 12 have no test output at all
(accuracy tables, per-item data or plots: a verdict would need a test this analysis would
have to invent), 4 report only a p-value (a correlation without n, pairwise p-values
without estimates), and 1 is now several candidates; 1 of the 15 ambiguous pairs was
resolved (by the hypothesis); of the 4 unreadable pairs (one empty source file), 2 are
several candidates and 2 have no test output. Of the 103 completed runs, 61 give a
primary comparison under v0.2 (47 from `results.json` as in v0.1, 2 more from it by the
hypothesis rule; 7 from `to_save/`, 1 of them by the hypothesis; 5 from `log.json`, 1 of
them by the plan), 18 stay ambiguous, 22 have no test output and 2 a p-value only. No file
needed the literal reader. The rule as preregistered recovered 32 pairs (49.23%), 2 more,
because it picked the comparison with the longest name when the plan named every
candidate (deviation 1).

| Check | v0.1 | v0.2 |
|---|---|---|
| F1, of the recoverable pairs | `proxy` 11, `not_comparable(conditions.pilot_mode)` 10, `same_quantity` 3 (of 24) | `proxy` 15, `not_comparable` 11, `same_quantity` 4 (of 30) |
| D1, of 65 | `no_data` 41, `underpowered` 15, `decidable` 9 | `no_data` 35, `underpowered` 18, `decidable` 10, `uncheckable` 2 |
| V1, of 65 | `reproduced` 4, `inconclusive` 61, `not_reproduced` 0 | `reproduced` 4, `inconclusive` 61, `not_reproduced` 0 |
| P2, of 65 | identical hypothesis wording in 1 pair | (unchanged) |

The v0.2 outcome distribution: `supported` 4; undecided because `no_data` 35,
`not_comparable` 11, `underpowered` 10, `misses_threshold` 2, `no_positive_control` 2,
`uncheckable` 1 (a source run whose mean difference is exactly 0). No pair changed its
verdict: the 4 reproduced pairs are the same, and every newly readable pair is
inconclusive (underpowered pilots, a pilot-mode setting written by one run only, no
random-agent control, or a zero source effect). In v0.1 the undecided reasons were
`no_data` 41, `not_comparable` 10, `underpowered` 7, `misses_threshold` 2,
`no_positive_control` 1.

A check added in v0.2: in 2 of the 4 reproduced pairs the source run's own mean
difference is negative (experimental below baseline; CodeScientist judged that source run
"refute"). The record's direction is the hypothesis's (experimental above baseline, the
bootstrap's own one-sided test), and the source effect enters only as a magnitude for
power, so the rubric reads these reruns as reproducing the hypothesis, not the source's
result. This is a property of the v0.1 design, unchanged here, and should be read with
the verdicts.

Per-comparison table (pairs whose primary stays ambiguous; never counted among the 65):
17 comparisons from 4 pairs are found in both runs: `reproduced` 3, `inconclusive` 14
(`no_positive_control` 7, `underpowered` 3, `not_comparable` 3, `misses_threshold` 1). All
3 reproduced comparisons are pairwise comparisons of state-representation levels whose
source run found the opposite sign; "baseline" and "experimental" there are only the
order of two levels, so the declared positive direction is not the hypothesis's.

Agreement with CodeScientist's own labels (its meta-analysis judges each run support,
refute or inconclusive from the run's write-up): our verdict for the reproduction run
matches theirs (reproduced ~ support, not_reproduced ~ refute, inconclusive ~
inconclusive) in 18 of 65 pairs (27.69%, 95% CI 18.29% to 39.58%) in both v0.1 and v0.2.
The v0.1 3 x 3 counts: where they say support, we say inconclusive in 25 and reproduced
in 2; where they say refute, we say inconclusive in all 20; where they say inconclusive,
we say inconclusive in 16 and reproduced in 2 (v0.2: the same cells). Most of the
disagreement is the rubric refusing to decide: among the v0.1 recoverable pairs, every
reproduction run they label refute (6) has a non-significant bootstrap p, where the
rubric's "rejected" also requires adequate power and a passing positive control. Against
their run-level consistency (the two runs' judgements the same or different): of 25 pairs
with the same judgement we call 2 reproduced and 23 inconclusive; of 40 with different
judgements, 2 and 38.

### (a') The batch without expert notes

The CodeScientist repository releases two full-50 batches: with expert notes (above) and
without. The second has bulk and meta-analysis tables in the repository, 94 completed
runs, which would give 60 (source, rerun) pairs, but no run outputs anywhere we looked:
its 250 run directories (named in `data/all-experiments.json`) are absent from the
full-50 archive (whose only top-level directory is the with-notes batch), from the
example-experiments archive (Table 4's 20 experiments: 10 from the with-notes batch, 10
follow-on runs) and from the repository tree, which has no other archive. The bulk table
holds only prose summaries of results, which a verdict read from numbers cannot use. The
batch is therefore counted, not judged (`reproduce.cs.batch2.*`); a separate group needs
the run outputs, which are not released.

### (b) DiscoveryBench planted effects and nulls (synthetic)

All 374 synthetic tasks; 183 of 903 queries give a target column and a gold expression.
A planted effect is (target, a column in its gold expression); a null is (target, a
column named by no query of the task), in tasks where every query is usable. Numeric and
true/false columns only. Each table's rows are split in halves with seed 0: half A is
the source, half B the reproduction; Pearson r, alpha 0.05 two-sided, minimum |r| 0.1,
direction from the source. Design in `analyses/reproduce/discoverybench_planted.py`.

| Group | n | reproduced | not_reproduced | inconclusive |
|---|---|---|---|---|
| planted | 358 | 171 | 2 | 185 (underpowered 181, misses threshold 4) |
| null | 1569 | 35 | 7 | 1527 (underpowered 1523, misses threshold 4) |

- Nulls are mostly not reproduced or inconclusive: 97.77% (95% CI 96.91% to 98.39%).
- Planted effects are NOT mostly reproduced overall: 47.77% (95% CI 42.64% to 52.94%).
  D1 classes about half of them underpowered: the planted functions are often
  non-linear or shared among several columns, so the marginal correlation on the
  source half is small and the reproduction half cannot detect it at that size. Among
  planted pairs D1 calls decidable, 96.61% reproduce (95% CI 92.8% to 98.44%; n = 177);
  among those whose source half was itself significant, 88.14% (n = 194).
- The 35 reproduced nulls are all significant on the whole table (35 of 35; 122 of the
  1569 nulls are). They are columns the generator made dependent on the target
  indirectly, so the "null" label is impure there; the verdict follows the data.
- Deliberately small reproductions (the first 10 rows of half B): classed underpowered
  in 85.02% of planted pairs (n = 327) and 99.72% of nulls (n = 1430). The planted pairs
  still called decidable at 10 rows are those with the largest source correlations. Checked
  against empirical power (200 random subsamples of 10 rows from half B, the same test):
  D1's class agrees with whether the empirical power reaches 0.8 in 96.64% of planted
  pairs and 99.86% of nulls.

**Sensitivity to the association measure (v0.2).** Is the underpowering a linear-measure
artefact? Two non-linear measures, fixed in the preregistration, beside the Pearson
results (which they do not replace):

| Group | Pearson: reproduced | Spearman: reproduced | Spearman: underpowered | detected on half B: Pearson / Spearman / binned MI |
|---|---|---|---|---|
| planted (358) | 47.77% | 47.49% (95% CI 42.37% to 52.66%) | 51.68% | 53.63% / 54.75% / 55.03% |
| null (1569) | 2.23% | 2.49% | 96.88% | 8.41% / 8.73% / 7.97% |

Spearman's rho gives the full verdict (same halves, thresholds and procedure; D1 by the
Fisher-z formula, an approximation for rho); among planted pairs it calls decidable,
98.27% reproduce (n = 173); nulls are not reproduced or inconclusive in 97.51%. Mutual
information after a fixed binning (by value up to 4 values, else quartiles; permutation p
from 199 permutations) has no closed-form power, so it gives detection only: it finds 29
planted pairs Pearson misses on half B, and 63 nulls. The answer is no: a rank or binned
dependence measure moves the planted detection rate by about one to one and a half
points, and D1 still classes about half the planted pairs underpowered. The missing power
is mostly weak marginal dependence (the target is spread over several columns), not the
shape of the relation.

**Coverage beyond the gold expressions (v0.2, derived).** Of the 903 queries, 520 give a
gold hypothesis in prose only and 200 give none. In a prose hypothesis a column is named
when its name, or its name with underscores read as spaces, occurs as a whole word. 127
hypotheses name exactly two columns: each gives one derived planted pair (no target is
known; the measures are symmetric). The others are not used: 90 name none, 117 one, and
186 three or more, where pairs among predictors need not be related. 33 derived pairs have
a non-numeric column, leaving 94: Pearson reproduces 26 (27.66%, 95% CI 19.63% to 37.44%),
none is not reproduced, 68 are inconclusive (66 underpowered); among the derived pairs D1
calls decidable, 92.86% reproduce (n = 28). Spearman reproduces 30 (31.91%). On half B,
Pearson detects 36.17%, Spearman 38.3%, MI 32.98%. Derived pairs carry no positive
control, and a two-name hypothesis may name two predictors instead of a target and a
predictor: they are a weaker label than the gold expression and are reported apart.

### (c) P1 on a scratch git repository, and the demo

`tests/reproduce/test_commit_order.py` builds temporary repositories and checks every
P1 outcome and reason, by declared refs and by the record file's history, including
unrelated histories, thresholds changed after the result and changed back, and an
unparseable old version of the record.

`examples/reproduce/demo_commit_order.py` shows the workflow P1 credits. It builds a
temporary git repository and commits `examples/reproduce/records/committed_first.yaml`
twice: first the plan (the test, the source numbers, the reproduction's quantity,
conditions and planned n, and the thresholds; no reproduction result), then the result.
The check passes P1 (`committed_first`) and exits 0:

```bash
python examples/reproduce/demo_commit_order.py
```

```text
c1f75ef plan: test and thresholds, before the run
a75b596 result: reproduction numbers
::notice file=committed_first.yaml,line=3::P2 hypothesis copy: verbatim
::notice file=committed_first.yaml,line=19::D1 decidability: decidable
::notice file=committed_first.yaml,line=19::F1 faithfulness: same_quantity
::notice file=committed_first.yaml,line=35::P1 commit order: committed_first
::notice file=committed_first.yaml,line=35::V1 verdict from the numbers: reproduced (supported)
{"decidability": "decidable", "faithfulness": "same_quantity", "outcome_label": "supported", "verdict": "reproduced"}
wrote reproduction_verdict.json
exit 0
```

Fixed commit identities and dates make the output byte-identical; nothing is written to
the user's git configuration (`--keep DIR` keeps the repository). Checked in place in
this repository, the same record fails P1 with `same_commit`, because here the plan and
the result arrive in one commit: that is why the quickstart on `supported.yaml` exits 1.

## Limits

- The record is the input. Faithfulness (same quantity, proxy, substitution) is a
  judgement the record DECLARES; F1 checks the declaration against what can be checked
  (names, units, effect types, conditions) but cannot tell a well-named substitution
  from a reproduction.
- Power is closed-form for four effect types and assumes the test the type implies (a
  correlation test, a two-sample or one-sample t, a two-proportion z). Other designs are
  `uncheckable`, not approximated. Power is at the source effect, which is itself an
  estimate (often inflated when the source was selected for being surprising).
- One record is one committed component. `partly_supported` comes only from
  `aggregate()` over several records; the CLI checks one record at a time.
- P1 trusts git: commit order in the graph, not wall-clock truth. Rewritten history can
  fake it; a signed or pushed history is stronger evidence than this check.
- P2 compares text after a fixed normalisation; it cannot tell a faithful paraphrase
  from a distortion, so any rewording is an error by design.
- (a) CodeScientist reruns are reruns in the same environment, not independent data in
  the asta-flows sense; its thresholds (one-sided alpha 0.05, minimum effect 0 on the
  mean difference, direction experimental above baseline) were fixed by this analysis,
  not by the runs' authors. The direction is the hypothesis's, not the source run's
  observed sign: 2 of the 4 reproduced pairs have a source run whose own mean difference
  is negative. The effect size is derived from the one-sided bootstrap p by a normal
  approximation. The primary comparison is identified by a fixed rule (v0.1: the single
  non-random bootstrap block of `results.json`; v0.2: three files in order, then the
  hypothesis and the plan by word matching); where it finds no or several candidates the
  pair is `no_data`: 41 of 65 in v0.1, 35 in v0.2. Word matching is lexical: it can pick
  the comparison whose name shares the hypothesis's words without being the one the
  hypothesis means, and it cannot choose among comparisons the plan names equally. The
  v0.2 rule was corrected once after seeing its choices (the deviations file); both
  versions are reported. 18 pairs (14 with no test output, 4 with a p-value only) cannot
  be judged without inventing a test. CodeScientist's labels are a language-model reading
  of each run's write-up, not ground truth. The batch without expert notes has no
  released run outputs and is not judged.
- (b) "Planted" means in the gold expression, not "linearly detectable"; "null" means
  named by no query, not independent. Both labels come from the released metadata and
  are imperfect in the ways reported above. The halves come from one synthetic table.
  Derived planted pairs rest on exact column names in prose and may pair two predictors;
  Spearman's D1 uses an approximation; the mutual-information binning is one fixed
  choice, and MI gives detection only.
