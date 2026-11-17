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
| Receipts, SciArena: the response with the higher W1+W2 flag rate per citation loses the human vote more often | lost in 50.09% of included votes (95% CI 45.9% to 54.27%); exact sign test p = 1.0; 10,000-draw permutation p = 1.0 | 569 votes | **null** | `receipts.sciarena.heldout.*`, prereg `prereg/receipts/sciarena_prereg.md` (commit adb9f3e) |
| Audit H1, CodeScientist full-50 reruns: runs the audit flags agree less with the other runs of their idea | mean leave-one-out agreement 0.4408 for flagged runs against 0.3433 for passed runs; stratified permutation p = 0.0845 | 80 runs (38 flagged) | **not supported**; the difference is in the opposite direction and not significant | `audit.heldout.h1.*`, prereg `prereg/audit/heldout_prereg.md` (commit 3d86441), rules frozen at d24d2f7 |

The audit's H2 (external soundness ratings) was preregistered in the same file but uses
the 20 development papers, so it is labelled `exploratory`: mean binarised soundness
0.6667 for the 11 papers the audit passes against 0.6296 for the 9 it flags,
permutation p = 0.8561. **Null.**

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
| | W1: law states a number absent from its cited records | 37.78% | 35.62% to 40.0% | 1887 | descriptive |
| | ... in the novelty-focused condition (laws written as quantitative predictions) | 84.62% | 82.03% to 86.91% | 839 | descriptive |
| | ... in the accuracy-focused condition | 0.29% | 0.1% to 0.84% | 1048 | descriptive |
| | W1: evidence item gives a number absent from the records it cites | 5.28% | 4.8% to 5.8% | 7677 | descriptive |
| | W2: assertive law over hedged cited records | 0.11% | 0.03% to 0.39% | 1887 | descriptive |
| | W2: assertive evidence item over hedged records | 2.51% | 2.19% to 2.89% | 7677 | descriptive |
| | parse coverage: results files with at least one evidence record | 80.9% | 80.29% to 81.49% | 16316 | descriptive |
| SciArena-Eval (2000 votes) | inline citations that resolve to a listed citation with passage text | all but one | | 31820 | descriptive |
| | W1 per resolved inline citation | 1.42% | 1.3% to 1.56% | 31819 | descriptive |
| | W2 per resolved inline citation | 1.4% | 1.28% to 1.54% | 31819 | descriptive |
| | W1 or W2 | 2.8% | 2.62% to 2.99% | 31819 | descriptive |
| | quoted spans found verbatim in a cited passage | 20% | 5.67% to 50.98% | 10 | descriptive |

Exploratory, Theorizer: within each literature-supported condition, theories above and
below the median released predictive-accuracy support fraction do not differ detectably
in T1 (accuracy-focused permutation p 0.6677, n = 317) or W1 (p 0.1476; novelty-focused
p 0.7906, n = 115). Wide intervals on small groups. Detail: [receipts.md](receipts.md).

## C2. Experiment audit

| Data | Metric | Value | n | Label |
|---|---|---|---|---|
| CodeScientist Table 4 (19 discoveries) | rejected discoveries flagged by a code meant for the human reason | 9 | 13 | dev |
| | ... of those with a deterministic reason | 9 | 12 | dev |
| | rejected with any error-severity code | 6 | 13 | dev |
| | accepted with any error-severity code (false flags) | 3 | 6 | dev |
| | accepted with any flag | 6 | 6 | dev |
| DiscoveryBench synthetic tasks, A5 scan (157 scanned of 903) | distractor columns with raw p < 0.05 | 7.43% | 4456 tests | descriptive |
| | distractor columns with BH q < 0.05 | 2.74% | 4456 tests | descriptive |
| | distractor hits removed by BH | 63.14% | 331 hits | descriptive |
| | gold columns detected, raw / BH | 57.91% / 52.35% | 575 | descriptive |
| | permuted-target control: tasks with any hit, raw / BH | 73.25% / 3.82% | 157 | synthetic |
| | permuted-target control: hit rate per test, raw / BH | 4.73% / 0.12% | 5031 tests | synthetic |
| CodeScientist resistor report | table cells reproduced exactly from `results.json` | 9 | 9 | descriptive |

The synthetic AutoDiscovery fixtures (12 nodes, one clean, one uncheckable, ten with one
planted defect each) are a unit test, not a metric: the audit finds exactly the planted
codes. The A5 distractor counts are hits outside the gold relation, not necessarily
false discoveries; only the permuted-target control is false by construction. Detail and
the per-reason table: [audit.md](audit.md), `analyses/audit/dev_table.md`.

## C3. Reproduction verdict

| Data | Metric | Value | 95% CI | n | Label |
|---|---|---|---|---|---|
| CodeScientist full-50 reruns (24 ideas with 2+ completed runs) | (source, rerun) pairs whose numbers are recoverable in both runs | 36.92% | 26.23% to 49.08% | 65 | descriptive |
| | V1 verdicts: reproduced / not reproduced / inconclusive | 4 / 0 / 61 | | 65 | descriptive |
| | D1: no data / underpowered / decidable | 41 / 15 / 9 | | 65 | descriptive |
| | agreement with CodeScientist's own run labels | 27.69% | 18.29% to 39.58% | 65 | descriptive |
| DiscoveryBench synthetic, planted effects on held-out row halves | reproduced | 47.77% | 42.64% to 52.94% | 358 | synthetic |
| | reproduced, among pairs D1 calls decidable | 96.61% | 92.8% to 98.44% | 177 | synthetic |
| | underpowered when the reproduction has 10 rows | 85.02% | 80.74% to 88.48% | 327 | synthetic |
| | D1 class at 10 rows agrees with empirical power | 96.64% | 94.08% to 98.11% | 327 | synthetic |
| DiscoveryBench synthetic, nulls | not reproduced or inconclusive | 97.77% | 96.91% to 98.39% | 1569 | synthetic |
| | underpowered when the reproduction has 10 rows | 99.72% | 99.28% to 99.89% | 1430 | synthetic |
| | D1 class at 10 rows agrees with empirical power | 99.86% | 99.49% to 99.96% | 1430 | synthetic |

Most CodeScientist pairs are `inconclusive` because the rubric refuses to decide without
the numbers (`no_data`, 41 of 65) or with too few episodes (pilots, `underpowered`);
the low agreement with CodeScientist's labels is mostly that refusal. Planted effects are
not mostly reproduced overall because about half are underpowered on a half table; the
35 reproduced "nulls" are all significant on the whole table, so the null label is
impure there. Detail: [reproduce.md](reproduce.md).

## Determinism check

Each analysis was run twice from the cached data; `results/*.json` and the analysis
detail files were byte-identical between the runs and with the committed files (numpy
2.5.5, scipy 1.18.1). See [LIMITATIONS.md](LIMITATIONS.md) for what the numbers can and
cannot carry.
