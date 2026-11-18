# Preregistration: C2 experiment audit, rules v0.2, held-out test on unused CodeScientist runs

Committed before any scoring of these runs with these rules. Nothing in this file was
computed from the predictor or the outcome on the held-out units.

## What I had seen before writing this

- The development set (the 19 Table 4 discoveries) and its results under rules v0.1 and
  v0.2 (committed in fd0187a), including every error on an accepted discovery.
- The published v0.1 held-out result (H1, 80 full50 runs; H2, the 20 rated papers),
  including its per-run codes and outcomes in `analyses/audit/details/`.
- For the full50 archive: the directory names, which runs have a meta-analysis judgement,
  how many judged runs each idea has, and the judgement labels (support, refute,
  inconclusive) of the 13 held-out runs below, printed while checking which runs H1 left
  unused. The judgement is not this test's outcome.
- For the with-expert-notes bulk TSV: its column names, the counts of each
  `faithfullness_category` value over all 250 rows (43 faithful, 57 deviations, 3 errors,
  147 empty), and that all 13 held-out runs, and 79 of the 80 H1 runs, have a non-empty
  value. I have not seen the category of any individual run.
- I have not run the v0.2 audit on any full50 directory, and have not opened the files of
  the 13 held-out directories.

## Frozen rules

- Rules v0.2: the code in `consilience_ai2/audit/` at commit
  `fd0187a8c38d7682e78f980f5b760a43a818c305` (git tree
  `5aa8b9ccb6f4eda312cefb9a9ec1ad74ea657458` for that directory). Rules version string
  `audit-rules-2`.
- The scoring script (`analyses/audit/codescientist_heldout_v2.py`) checks that the tree
  of `consilience_ai2/audit` at scoring time is that tree. If it is not, every metric is
  relabelled `exploratory` with a caveat saying the rules changed after preregistration.
- Per-run audit: `analyses/audit/codescientist_common.audit_dir` (the CodeScientist adapter
  on one experiment directory, read in place from the zip, with no rerun labels supplied,
  so R2 is not evaluated).

## Which data are unused

The `codescientist-full50` archive is the with-expert-notes batch only (104 directories);
the without-expert-notes batch has meta-analysis files but no released run directories,
so it cannot be audited. Of the 104 directories, H1 scored 80, 10 are development-set
directories, and 14 were never audited: 13 runs of ideas with a single judged run and 1
run without a judgement, which is a development-set directory. So the unused, auditable
data are **13 runs**, none of them a development-set directory, none audited by v0.1 or
v0.2, and none a unit of H1 or H2. Two of them are runs of ideas whose other runs are in
the example-experiments archive (`knowledgegraphdiscovery`, `basicknowledgesharing`).

The reproduction component (C3) reads the same batch, but only for ideas with at least two
completed runs, and not for the audit or for this outcome.

## Hypothesis

- **H3 (confirmatory, rules v0.2).** Runs that the v0.2 audit flags at error severity are
  less often rated faithful to their experiment plan than runs it does not flag.

## Predictor

A run is **flagged** when its audit node has at least one check of severity `error` (codes
U1, A1, A3, A4, R1, R4, R5; R2 is not evaluated), i.e. verdict level `flag(error)` or
`refuse`; otherwise **passed** (`pass` or `flag(warning)`).

## Outcome, chosen before scoring

Leave-one-out rerun agreement (H1's outcome) is undefined here: each held-out run is the
only judged run of its idea. The meta-analysis judgement (support, refute, inconclusive)
says which way a run came out on its hypothesis, not whether the run is sound, and its
labels for these runs have been seen. The outcome is therefore the run's
`faithfullness_category` in the with-expert-notes bulk TSV of the `codescientist`
repository at commit 778b146
(`metaanalysis/*withexpertnotes*bulk.tsv`, matched by removing hyphens from
`experiment_name`, as for the meta-analysis): **1 when it is `faithful`, 0 when it is
`deviations` or `errors`**. It is CodeScientist's own per-run judgement of whether the
experiment was carried out as planned, which is what a reviewer checks first and what the
audit's errors are about (numbers the run did not print, columns it did not have, tests it
did not run, hard-coded results). It is model-generated (released data, not produced here)
and unseen for these runs.

## Test

- **Statistic.** T = share faithful among passed runs - share faithful among flagged runs.
  H3 predicts T > 0.
- **Test.** Two-sided permutation test, labels permuted across all units (one run per
  idea, so no strata), 10,000 permutations drawn with `numpy.random.default_rng(20261118)`;
  p = (1 + #{|T_perm| >= |T_obs|}) / (1 + 10,000).
- **Alpha** 0.05, two-sided. H3 is the only confirmatory test; no correction.
- **Decision.** H3 is supported if p < 0.05 and T > 0. Otherwise it is not supported, and
  the result is reported as a null (or as a result in the wrong direction), with n per
  group, the group shares, T and p.
- **Power, stated in advance.** With 13 runs only a very large difference can reach
  p < 0.05; a null here is weak evidence either way and will be reported as such.

## Exclusions and missing data

- Units: the 13 directories above (full50 directories that are not development-set
  directories and were not H1 units). No other exclusion is made from the primary test.
- A run whose `faithfullness_category` is empty or missing is not a unit (none expected).
- A run directory the audit cannot read is not dropped: the audit returns `refuse` with
  U1, which is an error, so the run counts as flagged.
- If either group has fewer than 3 runs, the test is not run and the result is reported as
  "not testable", with the group sizes.

## Secondary analyses (reported, no decision, labelled exploratory)

(a) Two-sided Fisher exact test of the same 2 x 2 table (scipy).
(b) The primary test without the 2 runs of ideas in the example-experiments archive.
(c) The same predictor and outcome on the H1 units that have a faithfulness category (runs
    already used in the v0.1 held-out test, so not blind for the runs, although this
    outcome was not looked at), same permutation test and seed.
(d) The v0.1 predictor (any error-severity check under the frozen v0.1 rules) on the 13
    held-out runs, same test and seed, to compare the two rule versions on the same units.
(e) Per code, the number of held-out runs with that code at error or warning severity
    (descriptive).
