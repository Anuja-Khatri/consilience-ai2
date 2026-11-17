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
numbers do not depend on whether `consilience` is installed.

### (a) CodeScientist reruns as reproductions (descriptive)

The full-50 batch with expert notes (the batch whose run outputs are released): 50
ideas, 5 runs each. 24 ideas have at least 2 completed runs, giving 65 (source,
reproduction) pairs: the first completed run is the source, each later one a
reproduction. Design in `analyses/reproduce/codescientist_reruns.py`.

Coverage: the numbers (CodeScientist's own bootstrap comparison) are recoverable for
both runs in 24 of 65 pairs (36.9%, 95% CI 26.2% to 49.1%). The rest: 22 pairs have
no bootstrap block in a run's final results file, 15 have more than one candidate
comparison (several metrics or several baselines; fail-closed, no choice is made), 4
have an unreadable results file. These pairs are D1 `no_data`.

| Check | Outcome (n) |
|---|---|
| F1, of 24 recoverable pairs | `proxy` 11 (the runs name their comparison differently), `not_comparable(conditions.pilot_mode)` 10 (the pilot-mode setting is written by one run only), `same_quantity` 3 |
| D1, of 65 | `no_data` 41, `underpowered` 15, `decidable` 9 |
| V1, of 65 | `reproduced` 4, `inconclusive` 61, `not_reproduced` 0 |
| P2, of 65 | the two runs state the hypothesis in identical words in 1 pair |

The undecided reasons: `no_data` 41, `not_comparable` 10, `underpowered` 7,
`misses_threshold` 2, `no_positive_control` 1. Underpowered is common because
the runs are pilots (5 to 25 episodes in the recoverable pairs) and the source effects
are small.

Agreement with CodeScientist's own labels (its meta-analysis judges each run support,
refute or inconclusive from the run's write-up): our verdict for the reproduction run
matches theirs (reproduced ~ support, not_reproduced ~ refute, inconclusive ~
inconclusive) in 18 of 65 pairs (27.7%, 95% CI 18.3% to 39.6%). The 3 x 3 counts:
where they say support, we say inconclusive in 25 and reproduced in 2; where they say
refute, we say inconclusive in all 20; where they say inconclusive, we say inconclusive
in 16 and reproduced in 2. Most of the disagreement is the rubric refusing to decide:
among the recoverable pairs, every reproduction run they label refute (6) has a
non-significant bootstrap p, where the rubric's "rejected" also requires adequate power
and a passing positive control. Against their run-level consistency
(the two runs' judgements the same or different): of 25 pairs with the same judgement
we call 2 reproduced and 23 inconclusive; of 40 with different judgements, 2 and 38.

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

- Nulls are mostly not reproduced or inconclusive: 97.8% (95% CI 96.9% to 98.4%).
- Planted effects are NOT mostly reproduced overall: 47.8% (95% CI 42.6% to 52.9%).
  D1 classes about half of them underpowered: the planted functions are often
  non-linear or shared among several columns, so the marginal correlation on the
  source half is small and the reproduction half cannot detect it at that size. Among
  planted pairs D1 calls decidable, 96.6% reproduce (95% CI 92.8% to 98.4%; n = 177);
  among those whose source half was itself significant, 88.1% (n = 194).
- The 35 reproduced nulls are all significant on the whole table (35 of 35; 122 of the
  1569 nulls are). They are columns the generator made dependent on the target
  indirectly, so the "null" label is impure there; the verdict follows the data.
- Deliberately small reproductions (the first 10 rows of half B): classed underpowered
  in 85.0% of planted pairs (n = 327) and 99.7% of nulls (n = 1430). The planted pairs
  still called decidable at 10 rows are those with the largest source correlations. Checked
  against empirical power (200 random subsamples of 10 rows from half B, the same test):
  D1's class agrees with whether the empirical power reaches 0.8 in 96.6% of planted
  pairs and 99.9% of nulls.

### (c) P1 on a scratch git repository

`tests/reproduce/test_commit_order.py` builds temporary repositories and checks every
P1 outcome and reason, by declared refs and by the record file's history, including
unrelated histories, thresholds changed after the result and changed back, and an
unparseable old version of the record.

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
  mean difference) were fixed by this analysis, not by the runs' authors. The effect
  size is derived from the one-sided bootstrap p by a normal approximation. The primary
  comparison is identified by a fixed rule (the single non-random bootstrap block); where
  that rule finds no or several candidates the pair is `no_data`, which is 41 of 65.
  CodeScientist's labels are a language-model reading of each run's write-up, not ground
  truth.
- (b) "Planted" means in the gold expression, not "linearly detectable"; "null" means
  named by no query, not independent. Both labels come from the released metadata and
  are imperfect in the ways reported above. The halves come from one synthetic table.
