# C3 v0.2: deviations from the preregistered extraction rule

Preregistration: `prereg/reproduce/cs_extraction_v0_2.md` (commit 0df1320).

When: after one full run of the code as preregistered, before any v0.2 number was
committed. The run's choices of primary comparison and its labels were inspected; three
flaws were found in the rule itself. They are corrected here, and the numbers of BOTH the
rule as preregistered (`reproduce.cs.v0_2.as_preregistered.*`) and the corrected rule
(`reproduce.cs.v0_2.*`) are reported. The verdict code, thresholds and pairs are
unchanged. The DiscoveryBench part is unchanged.

## 1. Primary comparison: share of distinctive words, not their number

As preregistered, a candidate's score was the NUMBER of its distinctive words found in the
hypothesis or plan. That favours longer names: in three runs every candidate was named in
the experiment plan, and the candidate with the most words in its name was picked
(`word_overlap` over `jaccard` and `custom` twice; `find-living-thing` over `boil` and
`use-thermometer`). That is a choice the plan does not make, which the task forbids
("if still ambiguous, report every comparison separately rather than picking one").

Corrected: the score is the SHARE of the candidate's distinctive words found in the text
(a fully named candidate scores 1). A unique maximum above zero still wins; ties, including
"every candidate fully named", are ambiguous.

## 2. Labels: list items named by values; the cross-run key keeps word order

As preregistered, a list item was named `key=value` (`[level1=boolean,level2=numerical]`),
so field names such as `level1` entered the words of a label and the same comparison did
not match across runs that name their fields differently (`[baseline=boolean,
experimental=numerical]`, `boolean_vs_numerical`). And the cross-run key was a sorted SET
of words, so `A vs B` matched `B vs A`, a comparison in the other direction.

Corrected: a list item is named by its short string values in key order
(`[boolean,numerical]`); the cross-run key is the word sequence in order of appearance.
Only the per-comparison report and the word matching use labels; key paths, quantities
and the v0.1 reading are unchanged.

## 3. A zero mean difference is not an effect

The record's effect size is the paired dz implied by the one-sided bootstrap p
(`Phi^-1(1 - p) / sqrt(n)`, p clipped at 1/R). When every paired difference is 0 the
bootstrap p is 1 and dz is large and negative although the mean difference is exactly 0;
D1 then computes power at an effect that does not exist. The same happens, more mildly,
whenever the implied dz and the mean difference disagree in sign.

Corrected (fail closed): when the mean difference is 0, or its sign differs from the sign
of the implied dz, the effect size is left out of the record; for a source run D1 is then
`uncheckable` (no source effect) and the pair is inconclusive. This can only remove
verdicts, never add a `reproduced`. In the v0.1 reading only reproduction runs and runs of
single-run ideas are affected, never the source run of a pair, so the v0.1 pair verdicts
do not depend on it; they are left as they were.

Amendment, also before any v0.2 number was committed: leaving the effect size out made
F1 report `not_comparable(effect_size)` (one side with an effect size, the other
without) for the two pairs with a zero difference, a label that names the wrong cause. A
mean difference of exactly 0 is now recorded as a zero effect (dz = 0): on a source run
D1 then finds no source effect and is `uncheckable`; on a reproduction run V1 reads a
zero effect. Only a sign disagreement leaves the effect size out. Verdicts of those two
pairs are inconclusive either way.

## 4. The verdict rule: a reproduction tests the source's finding

Decided after the v0.2 extraction results were seen (in particular: in 2 of the 4
reproduced CodeScientist pairs the source run's own mean difference is negative while the
record's declared direction is positive). This is a change of the verdict rule, not of
extraction, and it changes conclusions; it is not presented as preregistered.

Rationale: a reproduction tests the source's finding, not the hypothesis wording. Under
the v0.1 rule the expected sign was the declared `direction` (in the CodeScientist
analysis, experimental above baseline, the bootstrap's one-sided test), and the source
effect entered only as a magnitude for power, so a rerun could "reproduce" a hypothesis
the source run itself contradicted.

Verdict rule v0.2 (`consilience_ai2/reproduce/decide.py`, the default of the CLI and the
API; `--rule v0.1` keeps the old rule):

- the expected direction is the sign of the source effect on the committed scale;
- the source claims an effect when that effect is not zero, at least the committed
  minimum effect in size, and significant in its own direction (a one-sided p in the
  record is in the declared direction; when the source's sign is the other one, its
  complement 1 - p is used; without a p, p is computed from the source's effect size
  and n);
- a source that claims no effect cannot be reproduced by a minimum-effect test: the
  record is `undecided(source_null)`. A record that commits an equivalence margin is
  judged by the two one-sided tests against it (equivalence mode, unchanged: it already
  tests the source's value, sign included);
- `no_data` and `not_identifiable` come before `source_null`; the other D1 classes after.

Reported: the v0.1 numbers unchanged (v0.1 rule); the v0.2 numbers with the v0.2 rule;
and, to separate the two changes, the v0.2 extraction with the v0.1 rule
(`reproduce.cs.v0_2.extraction_only.*`). The rule as preregistered
(`reproduce.cs.v0_2.as_preregistered.*`) keeps the v0.1 verdict rule it assumed. In the
DiscoveryBench analysis the v0.1 Pearson numbers keep the v0.1 rule; every v0.2 verdict
(Pearson, Spearman, derived pairs) uses the v0.2 rule.

Amendment to 4 (commit a1e60bc), before any number under the v0.2 verdict rule was
committed: the first run read one reproduction with a mean difference of exactly 0 and a
bootstrap p of 1 (ties) as significant in the other direction (1 - p = 0), which gave
`undecided(inconsistent_numbers)`. At an effect of exactly 0 there is no evidence in
either direction, so the complement is no longer taken there.

Second amendment to 4 (commit 6cdc34c), also before any number under the v0.2 verdict rule
was committed: with a one-sided test in the source's direction an opposite effect could
never be shown (row 5 needs significance in the other direction), so the first run
labelled two reruns that were significantly opposite to their source
`undecided(no_positive_control)`. Under v0.2 a one-sided record now also reads the
one-sided p in the other direction (1 - p); significant there, with the effect on the
other side, is `opposite_effect`. Two-sided tests and rule v0.1 are unchanged.
