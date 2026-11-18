# C3 v0.2: extraction and coverage rules, fixed before the v0.2 numbers

Component: reproduce (C3). This file is committed before any v0.2 number is computed
(`results/reproduce.json` is written in a later commit). The v0.1 numbers stay in the
results file under their v0.1 metric ids; the v0.2 numbers are added beside them.

What was known when this was written: the v0.1 results (coverage, outcome distribution),
the file formats in the CodeScientist full-50 archive (which files exist in each run's
final iteration, and that bootstrap blocks are also printed in `log.json` and saved under
`to_save/`), the candidate comparison names in the runs v0.1 found ambiguous, and the
DiscoveryBench metadata fields. No v0.2 verdict, coverage figure or sensitivity result
had been computed.

Nothing here changes the verdict logic (`consilience_ai2/reproduce`), the thresholds, the
pairs or the records' construction. Only coverage and parsing change.

## (a) CodeScientist reruns: extraction rule v0.2

Unchanged: the 65 (source, reproduction) pairs; one-sided alpha 0.05, minimum effect 0 on
the mean difference, power 0.8; the record fields; F1 fallback backend; P1 skipped.

A run's outputs are read from its final iteration, as in v0.1. Tiers, in order; the first
tier with at least one non-control bootstrap block (CodeScientist's signature:
`mean_baseline`, `mean_experimental`, `p_value`, `dataset_size`) is used:

1. `modal-output/results.json` (v0.1's only source: every run v0.1 could read is read the
   same way);
2. `modal-output/to_save/**/*.json`, pooled in path order, identical numbers kept once;
3. `modal-output/log.json`: each message's first balanced `{...}` (JSON, else the
   restricted literal reader below). Label: the message text before the brace without a
   final colon; when empty, the previous message's text if it ends with a colon. A label
   printed again replaces the earlier block (a later pilot stage); identical numbers
   under several labels are kept once (first label).

Controls: a block whose location (key path, file, or log label) contains "random" is a
positive control (v0.1's rule). Exactly one control in the tier gives the positive
control p.

Parsing (all files): UTF-8 (a BOM dropped), else cp1252. `json.loads` first (it accepts
`NaN` and `Infinity`); if that fails, a restricted literal reader that accepts only
dict, list, tuple, string, number and the names true/false/null, True/False/None,
nan/NaN, inf/Infinity, with trailing commas; nothing is executed. An empty file is
`empty`, not a parse error. Non-finite numbers in a block stay unreadable (fail closed).

Primary comparison when the tier has several candidates (decided per run):

- words of a label: lowercase alphanumeric words; one-letter and digits-only words
  dropped; a fixed stop list (function words and the generic words of a statistics
  printout: bootstrap, result, statistic, test, comparison, analysis, summary, metric,
  baseline, experimental, experiment, condition, value, mean, vs, versus, json, log, save
  and their plurals) dropped; a final "s" removed from words longer than 3 letters not
  ending in "ss". A list item in a key path is named by its short string fields
  (`[baseline=boolean,experimental=full]`).
- each candidate's distinctive words are its words minus the words every candidate
  shares. Count them in the run's stated hypothesis (bulk TSV `hypothesis`). A unique
  maximum above zero is the primary (basis `hypothesis`).
- otherwise the same count in the run's experiment plan (`experiment_description` in
  `data/all-experiments.json`, matched by the run directory in `experiment_path`): basis
  `experiment_plan`.
- otherwise no choice: the run is `ambiguous_primary` and the pair stays `no_data`.

Ambiguous pairs, reported separately: for a pair where one or both runs are ambiguous
(and neither is unreadable), every comparison whose word set matches exactly one
candidate in each run (the run's primary, for a run that has one) is judged as its own
record. These per-comparison verdicts are reported as their own table and never counted
among the 65 pairs.

Runs with no bootstrap block in any tier are classified, in this order:
`other_test_output` (a dict with a p-value, an estimate (correlation, statistic or
difference) and an n; not turned into a record, because the committed thresholds belong
to the one-sided bootstrap test), `test_output_incomplete` (a p-value without an estimate
or an n), `unreadable_results_file` (no output file parses), `no_test_output` (outputs
parse but report no test: descriptive metrics or per-item data only; a verdict would need
a test this analysis would have to invent).

Reported: coverage v0.1 and v0.2 on the same 65 pairs, the reasons, the run-level tier
and basis counts, the files that needed the literal reader, the D1/F1/V1 and outcome
distributions, agreement with CodeScientist's labels, the v0.1 to v0.2 verdict
transitions, and the per-comparison table.

## (a') The batch without expert notes

Searched for run outputs of the batch `full50-noexpertnotes`: run directory names from
`data/all-experiments.json` (`experiment_path`) looked up in the full-50 archive, the
example-experiments archive and the CodeScientist repository tree. If none is found, the
batch is documented as having no released run outputs and its completed runs and
potential pairs are counted, not judged.

## (b) DiscoveryBench: sensitivity and coverage

Unchanged: the v0.1 planted and null pairs, halves, Pearson records, verdicts, small
reproductions and empirical-power draws (same random stream).

Sensitivity, reported next to the Pearson results, never replacing them:

- Spearman's rho in place of Pearson's r for every planted and null pair: same halves,
  thresholds, direction rule and procedure; the positive control is the other gold
  predictor with the largest |rho| on half A. D1 uses type `r` with rho (Fisher-z
  approximation).
- Mutual information on half B after a fixed binning (by value for at most 4 distinct
  values, else quartiles), permutation p from 199 permutations of the target's bins
  (seed from seed 0 and the pair by SHA-256). No verdict (no closed-form power): the
  share of pairs whose association half B detects at p < 0.05 is reported for Pearson,
  Spearman and MI, per group.

Coverage, labelled derived: queries with a prose gold hypothesis (`true_hypothesis`) but
no gold expression. A column is named when its name, or its name with underscores read as
spaces, occurs in the hypothesis as a whole word, case-insensitive. Exactly two named
columns give one derived planted pair (unordered; no positive control); other counts are
reported and not used. Pairs already planted from a gold expression are not repeated.
Derived pairs get the Pearson verdict, the Spearman verdict and the MI detection, reported
as their own group.
