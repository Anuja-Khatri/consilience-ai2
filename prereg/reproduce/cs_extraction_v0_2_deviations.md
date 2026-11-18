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
