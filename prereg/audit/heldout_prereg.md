# Preregistration: C2 experiment audit, held-out tests on CodeScientist

Committed before any held-out scoring. Nothing in this file was computed from the
held-out predictor or outcome values. What I had seen before writing it: the development
results (the audit on the 19 Table 4 discoveries, committed in d24d2f7), the
external-review averages printed in Table 4 of the CodeScientist paper, the number of
judged runs per idea in the meta-analysis file (not their labels' agreement), and the
directory names in the full50 archive. I have not run the audit on any full50 directory.

## Frozen rules

- Rules: the code in `consilience_ai2/audit/` at commit
  `d24d2f7738496448b9c68fa529ce89cda7ce5c2d` (git tree
  `cca16a044d8074fd2672026af812a67dd6cafc31` for that directory). Rules version string
  `audit-rules-1`.
- The scoring script checks that the tree of `consilience_ai2/audit` at scoring time is
  that tree. If it is not, the held-out metrics are relabelled `exploratory` with a caveat
  saying the rules changed after preregistration.
- Per-run audit: `analyses/audit/codescientist_common.audit_dir` at the same commit (the
  CodeScientist adapter on one experiment directory, read in place from the zip, with no
  rerun labels supplied).

## Hypotheses

- **H1 (confirmatory).** Runs the audit flags have lower verdict consistency across
  reruns than runs it passes.
- **H2 (exploratory, not blind).** Papers the audit flags have lower external soundness
  ratings than papers it passes. The 20 rated papers are the 20 directories of the
  example-experiments archive, which contain the development set, so H2 cannot be blind and
  is reported as exploratory whatever its result.

## Predictor (both hypotheses)

A run is **flagged** when its audit node has at least one check of severity `error`
(codes U1, A1, A3, A4, R1, R4, R5; this includes every `refuse` verdict), and **passed**
otherwise. R2 is not evaluated (no rerun labels are supplied), because R2 would read the
same rerun judgements that define the H1 outcome.

Why error severity and not "any flag": in the development set the warning-level A7 (no
effect size) fired on 16 of 19 discoveries, so "any flag" would leave almost no passed
runs; the error-level split was 9 of 19 flagged in development. This choice uses only the
development predictor distribution.

## H1: data, outcome, test

- **Data.** The `codescientist-full50` archive (the with-expert-notes batch: 50 ideas x 5
  runs) and, in the `codescientist` repository at commit 778b146, the with-expert-notes
  meta-analysis JSON (`metaanalysis/*withexpertnotes*meta-analysis.json`).
- **Units.** Experiment directories of the archive whose run (for example
  `simpleplanningagentcopy3`, matched by removing hyphens from the meta-analysis
  `specific_experiment_name`) has a per-run judgement (`support`, `refute` or
  `inconclusive`) in the meta-analysis file.
- **Exclusions, fixed in advance.** (1) Directories whose names equal a directory of the
  example-experiments archive (the development set's runs). (2) Runs of ideas with fewer
  than 2 judged runs (consistency undefined).
- **Outcome.** Leave-one-out agreement: for run j of an idea with k judged runs (k >= 2),
  the share of the idea's other k - 1 judged runs whose judgement equals run j's. All
  judged runs of the idea count as siblings, including excluded development runs.
- **Statistic.** T = mean outcome of passed runs - mean outcome of flagged runs. H1
  predicts T > 0.
- **Test.** Two-sided stratified permutation test: within each idea, the flagged/passed
  labels are permuted among that idea's eligible runs; 10,000 permutations drawn with
  `numpy.random.default_rng(20261117)`; p = (1 + #{|T_perm| >= |T_obs|}) / (1 + 10,000).
- **Decision.** H1 is supported if p < 0.05 and T > 0. Otherwise it is not supported, and
  the result is reported as a null (or as a result in the wrong direction), with n per
  group, the group means, T and p.
- **Secondary (reported, not used for the decision).** (a) Two-sided Mann-Whitney U test
  of the outcome between groups, unstratified, with the rank-biserial correlation. (b) The
  primary test repeated after also excluding every run of the 19 development ideas.
  (c) Per code, the mean outcome of runs with and without that code (descriptive, no test).

## H2: data, outcome, test

- **Data.** `reviews/codescientist_external_review_ratings.tsv` in the `codescientist`
  repository (60 ratings: 3 per paper, 20 papers) and the 20 directories of the
  `codescientist-example-experiments` archive, matched by idea name.
- **Outcome.** Per paper, the mean binarised soundness of its ratings, using the paper's
  binarisation: "Unsound" is 0, every other soundness label is 1. Novelty is not used (the
  audit does not address novelty).
- **Statistic and test.** T = mean outcome of passed papers - mean outcome of flagged
  papers; two-sided permutation test (labels permuted across all 20 papers), 10,000
  permutations, `numpy.random.default_rng(20261117)`, p as for H1. Secondary: two-sided
  Mann-Whitney U.
- **Reporting.** Exploratory; reported with n per group, means, T and p, a null as a null.

## Alpha and multiplicity

Alpha 0.05, two-sided. H1 is the only confirmatory test, so no correction is applied to it.
H2 and every secondary analysis are reported without a decision.

## Missing data and failures

- A run directory that the audit cannot read is not dropped: the audit returns `refuse`
  with U1, which is an error, so the run counts as flagged.
- Runs with no judgement are not units. Ideas with fewer than 2 judged runs contribute no
  units.
- A paper with fewer than 3 ratings uses the mean of the ratings it has.
- If either group has fewer than 5 units in H1 (or 3 in H2), the test is not run and the
  result is reported as "not testable", with the group sizes.
