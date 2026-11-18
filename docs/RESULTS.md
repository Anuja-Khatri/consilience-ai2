# Results

What the three tools measured on data released by Ai2 and its collaborators, and on
synthetic fixtures. Every number here renders from `results/registry.json`
(`scripts/numbers_lock.py` checks this in CI). **Every metric**, with its value, 95%
interval, n, label and source, is in the generated table
[docs/tables/results.md](tables/results.md); the caveats and stated tests are in the
registry itself. This page groups the main ones and says what they mean.

Labels (`split` in the registry):

- `heldout`: the hypothesis, test and decision rule were committed in `prereg/` before
  scoring, with the rules frozen; the scoring commit comes after it in the history.
- `dev`: the rules were written knowing these data. Fit, not generalisation.
- `exploratory`: computed and reported, not decision-bearing.
- `descriptive`: a measured rate or count, no hypothesis.
- `synthetic`: planted fixtures or generated data, true by construction or by design.

Intervals are 95%: Wilson for rates unless stated, exact (Clopper–Pearson) for the
preregistered SciArena proportion. A blank interval means none was computed (counts,
p values, differences reported with a permutation p instead).

To regenerate: `consilience-ai2 fetch all`, then `python analyses/receipts/run.py`,
`python analyses/audit/run_all.py` and `python analyses/reproduce/run.py`, then
`make lock`. Reruns on the same data give the same bytes.

## Preregistered held-out tests

| Test | Result | n | Decision | Source |
|---|---|---|---|---|
| Receipts, SciArena: the response with the higher W1+W2 flag rate per citation (W1/W2 rules v0.1, frozen) loses the human vote more often | lost in 50.09% of included votes (95% CI 45.9% to 54.27%); exact sign test p = 1.0; 10,000-draw permutation p = 1.0 | 569 votes | **null** | `receipts.sciarena.heldout.*`, prereg `prereg/receipts/sciarena_prereg.md` (commit adb9f3e) |
| Audit H1 (rules v0.1), CodeScientist full-50 reruns: runs the audit flags agree less with the other runs of their idea | mean leave-one-out agreement 0.4408 for flagged runs against 0.3433 for passed runs; stratified permutation p = 0.0845 | 80 runs (38 flagged) | **not supported**; the difference is in the opposite direction and not significant | `audit.heldout.h1.*`, prereg `prereg/audit/heldout_prereg.md` (commit 3d86441), rules frozen at d24d2f7 |
| Audit H3 (rules v0.2), the 13 full-50 runs no version had audited: runs the audit flags at error severity are less often rated faithful to their plan | the v0.2 audit flags 1 of 13 runs at error severity and passes 12 | 13 runs | **not testable**: below the preregistered minimum of 3 runs per group, so no test was run | `audit.heldout_v2.h3.*`, prereg `prereg/audit/heldout_v2_prereg.md` (commit 75b85b4), rules frozen at fd0187a (tree 5aa8b9c) |

The audit's H2 (external soundness ratings) was preregistered in the same file but uses
the 20 development papers, so it is labelled `exploratory`: mean binarised soundness
0.6667 for the 11 papers the audit passes against 0.6296 for the 9 it flags,
permutation p = 0.8561. **Null.**

H3 being not testable is a limit of the data, not a null result: these 13 runs are the
only unused auditable public data. The frozen v0.1 rules also flag 1 of the 13.
Exploratory secondary, not blind for the runs: the same predictor and outcome on the 79
H1 units with a faithfulness category: 50% of the 42 passed runs and 37.84% of the 37
flagged runs were rated faithful, a difference in the predicted direction that is not
significant (permutation p = 0.3663).

Exploratory secondaries of the SciArena test, also null: W1 alone 44.28% (n = 271,
sign-test p 0.068), W2 alone 52.3% (n = 348, p 0.4214).

## C1. Evidence receipts

| Data | Metric | Value | 95% CI | n | Label |
|---|---|---|---|---|---|
| Seeded synthetic workspace | planted defects found (exact code, file, line, key) | 100% | | 17 | synthetic |
| | error or warning findings on the clean controls | 0 | | 14 control spans | synthetic |
| asta-plugins example workspace | errors and warnings | 0 | | 1 span | descriptive |
| Theorizer (2856 theories, 4187 laws) | T1: cited evidence IDs that resolve to no record, per (law, ID) pair | 1.36% | 1.18% to 1.56% | 14343 | descriptive |
| | theories with at least one T1 | 0.52% | 0.25% to 1.08% | 1338 | descriptive |
| | T1 links using the export's fallback file name | 100% | | 205 | descriptive |
| | T2: laws with an empty scope or an empty evidence list | 0.88% | 0.64% to 1.22% | 4187 | descriptive |
| | W1 (rules v0.1): law states a number absent from its cited records | 37.78% | 35.62% to 40.0% | 1887 | descriptive |
| | ... in the novelty-focused condition (laws written as quantitative predictions) | 84.62% | 82.03% to 86.91% | 839 | descriptive |
| | ... in the accuracy-focused condition | 0.29% | 0.1% to 0.84% | 1048 | descriptive |
| | W1 (rules v0.1): evidence item gives a number absent from the records it cites | 5.28% | 4.8% to 5.8% | 7677 | descriptive |
| | W2 (rules v0.1): assertive law over hedged cited records | 0.11% | 0.03% to 0.39% | 1887 | descriptive |
| | W2 (rules v0.1): assertive evidence item over hedged records | 2.51% | 2.19% to 2.89% | 7677 | descriptive |
| | W1 (rules v0.2): law / evidence item | 37.73% / 5.18% | 35.57% to 39.94% / 4.71% to 5.7% | 1887 / 7677 | descriptive |
| | W1 (rules v0.2), law, novelty-focused / accuracy-focused | 84.51% / 0.29% | | 839 / 1048 | descriptive |
| | W2 (rules v0.2): law / evidence item | 0.16% / 2.45% | 0.05% to 0.47% / 2.13% to 2.82% | 1887 / 7677 | descriptive |
| | parse coverage: results files with at least one evidence record | 80.9% | 80.29% to 81.49% | 16316 | descriptive |
| SciArena-Eval (2000 votes) | inline citations that resolve to a listed citation with passage text | all but one | | 31820 | descriptive |
| | W1 per resolved inline citation (rules v0.1) | 1.42% | 1.3% to 1.56% | 31819 | descriptive |
| | W2 per resolved inline citation (rules v0.1) | 1.4% | 1.28% to 1.54% | 31819 | descriptive |
| | W1 or W2 (rules v0.1) | 2.8% | 2.62% to 2.99% | 31819 | descriptive |
| | W1 / W2 / either, rules v0.2 | 1.5% / 1.65% / 3.11% | 1.37% to 1.64% / 1.52% to 1.8% / 2.93% to 3.31% | 31819 | descriptive |
| | quoted spans found verbatim in a cited passage | 20% | 5.67% to 50.98% | 10 | descriptive |
| Precision sample (25 SciArena + 25 Theorizer flagged units per check and version, read by hand) | W1 precision, rules v0.1 | 54% | 40.4% to 67.0% | 50 | dev |
| | W1 precision, rules v0.2 | 56% | 42.3% to 68.8% | 50 | dev |
| | W2 precision, rules v0.1 | 26% | 15.9% to 39.6% | 50 | dev |
| | W2 precision, rules v0.2 | 32% | 20.8% to 45.8% | 50 | dev |

The precision sample has one annotator, the author of the rules, so it is labelled dev;
the differences between versions are inside the intervals. W2 is opt-in in the checker
because on this hand-checked sample only about a third of its flags were real overreach;
W1 stays on by default, as a warning. The W2 rates above are computed explicitly by the
analyses and do not depend on that default.

Exploratory, Theorizer: within each literature-supported condition, theories above and
below the median released predictive-accuracy support fraction do not differ detectably
in T1 (accuracy-focused permutation p 0.6677, n = 317) or W1 (p 0.1476; novelty-focused
p 0.7906, n = 115). Wide intervals on small groups. Detail: [receipts.md](receipts.md).

## C2. Experiment audit

| Data | Metric | Value | n | Label |
|---|---|---|---|---|
| CodeScientist Table 4 (19 discoveries), rules v0.1 / v0.2 | rejected discoveries flagged by a code meant for the human reason | 9 / 8 | 13 | dev |
| | ... of those with a deterministic reason | 9 / 8 | 12 | dev |
| | rejected with any error-severity code | 6 / 8 | 13 | dev |
| | rejected with any error or warning | 13 / 12 | 13 | dev |
| | accepted with any error-severity code (false flags) | 3 / 3 | 6 | dev |
| | accepted with any error or warning | 6 / 5 | 6 | dev |
| | discoveries with A7 (no effect size): a flag in v0.1, an info note in v0.2 | 16 / 16 | 19 | dev |
| DiscoveryBench synthetic tasks, A5 scan (157 scanned of 903) | distractor columns with raw p < 0.05 | 7.43% | 4456 tests | descriptive |
| | distractor columns with BH q < 0.05 | 2.74% | 4456 tests | descriptive |
| | distractor hits removed by BH | 63.14% | 331 hits | descriptive |
| | gold columns detected, raw / BH | 57.91% / 52.35% | 575 | descriptive |
| | permuted-target control: tasks with any hit, raw / BH | 73.25% / 3.82% | 157 | synthetic |
| | permuted-target control: hit rate per test, raw / BH | 4.73% / 0.12% | 5031 tests | synthetic |
| DiscoveryBench, A5 derived set (rules v0.2: 720 queries without a machine-readable relation; 483 scanned) | distractor columns with raw p < 0.05 / BH q < 0.05 | 7.42% / 2.79% | 15356 tests | descriptive |
| | distractor hits removed by BH | 62.42% | 1139 hits | descriptive |
| | derived gold columns detected, raw / BH | 35.15% / 30.3% | 1010 | descriptive |
| | permuted-target control: tasks with any hit, raw / BH | 79.5% / 6.63% | 483 | synthetic |
| | coverage of the 903 queries: machine-readable relation / machine-readable or derived | 17.39% / 70.87% | 903 | descriptive |
| CodeScientist resistor report | table cells reproduced exactly from `results.json` | 9 | 9 | descriptive |

The synthetic AutoDiscovery fixtures (12 nodes, one clean, one uncheckable, ten with one
planted defect each) are a unit test, not a metric: the audit finds exactly the planted
codes. The A5 distractor counts are hits outside the gold relation, not necessarily
false discoveries; only the permuted-target control is false by construction. The derived
relation comes from a fixed rule that names the target and gold columns from the query
text; it often picks the wrong target (it equals `target_col` in 32.68% of the 153
machine-readable queries it can be compared on), so its distractor numbers are less clean.

In v0.2, 3 of 6 accepted discoveries still carry an error. Two are genuine issues the
reviewers did not flag: discovery 5's SD 15.8% appears in no output (recomputed from the
run it is 16.2% sample / 16.0% population), and discovery 3 says "significantly" with no
test. The third is a new R2 error: discovery 2's idea has 2 supporting and 2 refuting
reruns. Detail and the per-reason table: [audit.md](audit.md),
`analyses/audit/dev_table.md`.

## C3. Reproduction verdict

| Data | Metric | Value | 95% CI | n | Label |
|---|---|---|---|---|---|
| CodeScientist full-50 reruns (24 ideas with 2+ completed runs) | (source, rerun) pairs whose numbers are recoverable in both runs | 36.92% | 26.23% to 49.08% | 65 | descriptive |
| | V1 verdicts: reproduced / not reproduced / inconclusive | 4 / 0 / 61 | | 65 | descriptive |
| | D1: no data / underpowered / decidable | 41 / 15 / 9 | | 65 | descriptive |
| | agreement with CodeScientist's own run labels | 27.69% | 18.29% to 39.58% | 65 | descriptive |
| CodeScientist, v0.2 (extraction v0.2, verdict rule v0.2) | pairs recoverable in both runs | 46.15% | 34.59% to 58.15% | 65 | descriptive |
| | V1 verdicts: reproduced / not reproduced / inconclusive | 2 / 2 / 61 | | 65 | descriptive |
| | D1: no data / underpowered / decidable / uncheckable | 35 / 18 / 10 / 2 | | 65 | descriptive |
| | agreement with CodeScientist's own run labels | 27.69% | 18.29% to 39.58% | 65 | descriptive |
| | per comparison (pairs whose primary is ambiguous): reproduced / not reproduced / inconclusive | 6 / 4 / 7 | | 17 comparisons from 4 pairs | descriptive || DiscoveryBench synthetic, planted effects on held-out row halves | reproduced | 47.77% | 42.64% to 52.94% | 358 | synthetic |
| | reproduced, among pairs D1 calls decidable | 96.61% | 92.8% to 98.44% | 177 | synthetic |
| | underpowered when the reproduction has 10 rows | 85.02% | 80.74% to 88.48% | 327 | synthetic |
| | D1 class at 10 rows agrees with empirical power | 96.64% | 94.08% to 98.11% | 327 | synthetic |
| DiscoveryBench synthetic, nulls | not reproduced or inconclusive | 97.77% | 96.91% to 98.39% | 1569 | synthetic |
| | underpowered when the reproduction has 10 rows | 99.72% | 99.28% to 99.89% | 1430 | synthetic |
| | D1 class at 10 rows agrees with empirical power | 99.86% | 99.49% to 99.96% | 1430 | synthetic |
| DiscoveryBench, sensitivity to the measure (v0.2), planted | reproduced with Spearman's rho | 47.49% | 42.37% to 52.66% | 358 | synthetic |
| | Spearman: underpowered / reproduced among decidable | 51.68% / 98.27% | | 358 / 173 | synthetic |
| | detected on half B: Pearson / Spearman / binned MI | 53.63% / 54.75% / 55.03% | | 358 | synthetic |
| DiscoveryBench, sensitivity to the measure (v0.2), nulls | reproduced: Pearson / Spearman | 2.23% / 2.49% | | 1569 | synthetic |
| | detected on half B: Pearson / Spearman / binned MI | 8.41% / 8.73% / 7.97% | | 1569 | synthetic |
| DiscoveryBench, derived pairs (v0.2: prose hypotheses naming two numeric columns) | reproduced (Pearson) | 27.66% | 19.63% to 37.44% | 94 | synthetic |
| | reproduced among pairs D1 calls decidable | 92.86% | | 28 | synthetic |
| | reproduced with Spearman's rho | 31.91% | | 94 | synthetic |

Most CodeScientist pairs are `inconclusive` because the rubric refuses to decide without
the numbers (`no_data`, 41 of 65) or with too few episodes (pilots, `underpowered`);
the low agreement with CodeScientist's labels is mostly that refusal. Planted effects are
not mostly reproduced overall because about half are underpowered on a half table; the
35 reproduced "nulls" are all significant on the whole table, so the null label is
impure there.

v0.2 changes the extraction (more files read, tolerant parsing; preregistered in
`prereg/reproduce/cs_extraction_v0_2.md`, with deviations recorded) and the verdict rule:
the expected direction is now the sign of the source effect, not the declared direction.
The verdict-rule change was decided after the v0.2 extraction results were seen. The
extraction alone changes no verdict (4 / 0 / 61). The rule turns 2 of the 4 v0.1
"reproduced" pairs into `not_reproduced` (`opposite_effect`): their source run's own
effect is significantly negative and the rerun is significantly positive, so v0.1 read
them as reproducing the hypothesis wording while they contradict the source's finding.
On DiscoveryBench, rank and binned measures move planted detection by about one to one
and a half points, and Spearman still classes about half the planted pairs
underpowered: the missing power is weak marginal dependence, not the shape of the
relation. Detail: [reproduce.md](reproduce.md).

## Determinism check

Each analysis was run twice from the cached data; `results/*.json` and the analysis
detail files were byte-identical between the runs and with the committed files (numpy
2.5.5, scipy 1.18.1). See [LIMITATIONS.md](LIMITATIONS.md) for what the numbers can and
cannot carry.
