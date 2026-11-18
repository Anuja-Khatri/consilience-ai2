# Results table

Rendered from `results/registry.json` by `scripts/numbers_lock.py`; do not edit.
Every metric the project reports, grouped by component. `split` is the label:
`heldout` (preregistered before scoring), `dev` (rules written knowing the data),
`exploratory`, `descriptive` (a measured rate, no hypothesis) or `synthetic`
(planted fixtures, true by construction). Caveats are in the registry.

## audit

| metric | value | 95% CI | n | split | source | what | test / prereg |
|---|---|---|---|---|---|---|---|
| audit.dev.accepted_flagged_any | 6 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags: accepted discoveries with any error or warning (discoveries) |  |
| audit.dev.accepted_flagged_error | 3 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags: accepted discoveries with any error-severity code (discoveries) |  |
| audit.dev.code.a1.accepted | 3 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.a1.rejected | 3 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.a2.accepted | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.a2.rejected | 1 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.a4.accepted | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.a4.rejected | 0 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.a5.accepted | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.a5.rejected | 1 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.a6.accepted | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.a6.rejected | 2 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.a7.accepted | 4 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.a7.rejected | 12 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.r1.accepted | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.r1.rejected | 4 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.r2.accepted | 4 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.r2.rejected | 4 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.code.r3.accepted | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (discoveries) |  |
| audit.dev.code.r3.rejected | 1 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.reason.built_but_unused.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | the agents never use the graph they build: flagged by R5 (discoveries) |  |
| audit.dev.reason.effect_vanished_at_scale.caught | 3 |  | 3 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | effect did not replicate with more samples: flagged by R2/R3/A6 (discoveries) |  |
| audit.dev.reason.few_samples_unvalidated_metric.caught | 1 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | overly simple benchmark, few samples, judge metric not validated: flagged by R3/A2 (discoveries) |  |
| audit.dev.reason.foregone_conclusion_hardcoded.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | both conditions hard-coded: a foregone conclusion: flagged by R4 (discoveries) |  |
| audit.dev.reason.partly_hardcoded_agent.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | agent partly hard-coded: flagged by R4 (discoveries) |  |
| audit.dev.reason.random_only_baseline.caught | 4 |  | 4 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | baseline too simple (a random agent): flagged by R1 (discoveries) |  |
| audit.dev.reason.report_lacks_details.caught | 1 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | report lacks details to evaluate: flagged by A2/A4/A7 (discoveries) |  |
| audit.dev.reason.unclear_motivation.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | unclear motivation and utility: flagged by no code (out of scope) (discoveries) |  |
| audit.dev.rejected_flagged_any | 13 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with any error or warning (discoveries) |  |
| audit.dev.rejected_flagged_error | 6 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with any error-severity code (discoveries) |  |
| audit.dev.rejected_flagged_intended | 9 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.rejected_in_scope_flagged_intended | 9 |  | 12 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | (discoveries) |  |
| audit.dev.v1.matrix.accepted.flag_error | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict flag(error) (discoveries) |  |
| audit.dev.v1.matrix.accepted.flag_warning | 3 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict flag(warning) (discoveries) |  |
| audit.dev.v1.matrix.accepted.pass | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict pass (discoveries) |  |
| audit.dev.v1.matrix.accepted.refuse | 3 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict refuse (discoveries) |  |
| audit.dev.v1.matrix.rejected.flag_error | 3 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict flag(error) (discoveries) |  |
| audit.dev.v1.matrix.rejected.flag_warning | 7 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict flag(warning) (discoveries) |  |
| audit.dev.v1.matrix.rejected.pass | 0 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict pass (discoveries) |  |
| audit.dev.v1.matrix.rejected.refuse | 3 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict refuse (discoveries) |  |
| audit.dev.v2.accepted_flagged_any | 5 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags: accepted discoveries with any error or warning (discoveries) |  |
| audit.dev.v2.accepted_flagged_error | 3 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags: accepted discoveries with any error-severity code (discoveries) |  |
| audit.dev.v2.code.a1.accepted | 2 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.a1.accepted_error | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.a1.rejected | 3 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.code.a2.accepted | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.a2.accepted_error | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.a2.rejected | 1 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.code.a4.accepted | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.a4.accepted_error | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.a4.rejected | 0 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.code.a5.accepted | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.a5.accepted_error | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.a5.rejected | 1 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.code.a6.accepted | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.a6.accepted_error | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.a6.rejected | 2 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.code.r1.accepted | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.r1.accepted_error | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.r1.rejected | 4 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.code.r2.accepted | 4 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.r2.accepted_error | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.r2.rejected | 4 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.code.r3.accepted | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code (error or warning) (discoveries) |  |
| audit.dev.v2.code.r3.accepted_error | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | false flags by this code at error severity (discoveries) |  |
| audit.dev.v2.code.r3.rejected | 1 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged by this code (discoveries) |  |
| audit.dev.v2.discovery5.accuracy_sd_population | 0.1605 |  | 50 | dev | fetch:codescientist-example-experiments | population SD of per-game accuracy (games) |  |
| audit.dev.v2.discovery5.accuracy_sd_sample | 0.1621 |  | 50 | dev | fetch:codescientist-example-experiments | sample SD of per-game accuracy (games) |  |
| audit.dev.v2.matrix.accepted.flag_error | 3 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict flag(error) (discoveries) |  |
| audit.dev.v2.matrix.accepted.flag_warning | 2 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict flag(warning) (discoveries) |  |
| audit.dev.v2.matrix.accepted.pass | 1 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict pass (discoveries) |  |
| audit.dev.v2.matrix.accepted.refuse | 0 |  | 6 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | accepted discoveries with verdict refuse (discoveries) |  |
| audit.dev.v2.matrix.rejected.flag_error | 8 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict flag(error) (discoveries) |  |
| audit.dev.v2.matrix.rejected.flag_warning | 4 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict flag(warning) (discoveries) |  |
| audit.dev.v2.matrix.rejected.pass | 1 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict pass (discoveries) |  |
| audit.dev.v2.matrix.rejected.refuse | 0 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with verdict refuse (discoveries) |  |
| audit.dev.v2.notes.a7 | 16 |  | 19 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | discoveries with an A7 info note (no effect size): a reporting convention, not a flag (discoveries) |  |
| audit.dev.v2.reason.built_but_unused.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | the agents never use the graph they build: flagged by R5 (discoveries) |  |
| audit.dev.v2.reason.effect_vanished_at_scale.caught | 3 |  | 3 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | effect did not replicate with more samples: flagged by R2/R3/A6 (discoveries) |  |
| audit.dev.v2.reason.few_samples_unvalidated_metric.caught | 1 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | overly simple benchmark, few samples, judge metric not validated: flagged by R3/A2 (discoveries) |  |
| audit.dev.v2.reason.foregone_conclusion_hardcoded.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | both conditions hard-coded: a foregone conclusion: flagged by R4 (discoveries) |  |
| audit.dev.v2.reason.partly_hardcoded_agent.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | agent partly hard-coded: flagged by R4 (discoveries) |  |
| audit.dev.v2.reason.random_only_baseline.caught | 4 |  | 4 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | baseline too simple (a random agent): flagged by R1 (discoveries) |  |
| audit.dev.v2.reason.report_lacks_details.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | report lacks details to evaluate: flagged by A2/A4/A7 (discoveries) |  |
| audit.dev.v2.reason.unclear_motivation.caught | 0 |  | 1 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | unclear motivation and utility: flagged by no code (out of scope) (discoveries) |  |
| audit.dev.v2.rejected_flagged_any | 12 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with any error or warning (discoveries) |  |
| audit.dev.v2.rejected_flagged_error | 8 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries with any error-severity code (discoveries) |  |
| audit.dev.v2.rejected_flagged_intended | 8 |  | 13 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | rejected discoveries flagged (error or warning) by a code meant for their reason (discoveries) |  |
| audit.dev.v2.rejected_in_scope_flagged_intended | 8 |  | 12 | dev | fetch:codescientist-example-experiments + fetch:codescientist (metaanalysis) | as above, without the unclear-motivation rejection (discoveries) |  |
| audit.discoverybench.coverage_machine | 0.1739 |  | 903 | descriptive | fetch:discoverybench |  |  |
| audit.discoverybench.coverage_machine_or_derived | 0.7087 |  | 903 | descriptive | fetch:discoverybench |  |  |
| audit.discoverybench.derived.agreement.column_precision | 0.9596 |  | 520 | descriptive | fetch:discoverybench | pooled share of derived relation columns (target and gold) that are in the machine-readable relation (relevant_cols and target_col) |  |
| audit.discoverybench.derived.agreement.column_recall | 0.6845 |  | 729 | descriptive | fetch:discoverybench | pooled share of machine-readable relation columns that the rule also derives |  |
| audit.discoverybench.derived.agreement.target | 0.3268 |  | 153 | descriptive | fetch:discoverybench | derived target equals target_col (50) |  |
| audit.discoverybench.derived.agreement.usable | 153 |  | 183 | descriptive | fetch:discoverybench | machine-readable queries for which the rule derives a target and at least one gold column (tasks) |  |
| audit.discoverybench.derived.distractor_hit_rate_bh | 0.0279 |  | 15356 | descriptive | fetch:discoverybench | distractor columns with BH q < 0.05 (428) | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.derived.distractor_hit_rate_raw | 0.0742 |  | 15356 | descriptive | fetch:discoverybench | distractor columns with raw p < 0.05 (1139) | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.derived.distractor_hit_reduction | 0.6242 |  | 1139 | descriptive | fetch:discoverybench | 1 - (BH hits / raw hits) among distractor columns |  |
| audit.discoverybench.derived.distractor_tests | 15356 |  | 483 | descriptive | fetch:discoverybench | (column tests) |  |
| audit.discoverybench.derived.gold_recall_bh | 0.303 |  | 1010 | descriptive | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.derived.gold_recall_raw | 0.3515 |  | 1010 | descriptive | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.derived.null_hit_rate_bh | 0.0023 |  | 16366 | synthetic | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05; target permuted, numpy default_rng(seed 20261117 + task index) |
| audit.discoverybench.derived.null_hit_rate_raw | 0.0517 |  | 16366 | synthetic | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05; target permuted, numpy default_rng(seed 20261117 + task index) |
| audit.discoverybench.derived.null_tasks_any_hit_bh | 0.0663 |  | 483 | synthetic | fetch:discoverybench |  |  |
| audit.discoverybench.derived.null_tasks_any_hit_raw | 0.795 |  | 483 | synthetic | fetch:discoverybench |  |  |
| audit.discoverybench.derived.tasks_scanned | 483 |  | 720 | descriptive | fetch:discoverybench | (tasks) |  |
| audit.discoverybench.derived.tasks_with_distractor_hit_bh | 0.4224 |  | 483 | descriptive | fetch:discoverybench |  |  |
| audit.discoverybench.derived.tasks_with_distractor_hit_raw | 0.853 |  | 483 | descriptive | fetch:discoverybench |  |  |
| audit.discoverybench.derived.tasks_without_machine_gold | 720 |  | 903 | descriptive | fetch:discoverybench | (tasks) |  |
| audit.discoverybench.distractor_hit_rate_bh | 0.0274 |  | 4456 | descriptive | fetch:discoverybench | distractor columns with BH q < 0.05 (122) | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.distractor_hit_rate_raw | 0.0743 |  | 4456 | descriptive | fetch:discoverybench | distractor columns with raw p < 0.05 (331) | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.distractor_hit_reduction | 0.6314 |  | 331 | descriptive | fetch:discoverybench | 1 - (BH hits / raw hits) among distractor columns |  |
| audit.discoverybench.distractor_hits_bh | 122 |  | 4456 | descriptive | fetch:discoverybench | (column tests) |  |
| audit.discoverybench.distractor_hits_raw | 331 |  | 4456 | descriptive | fetch:discoverybench | (column tests) |  |
| audit.discoverybench.distractor_tests | 4456 |  | 157 | descriptive | fetch:discoverybench | (column tests) |  |
| audit.discoverybench.gold_recall_bh | 0.5235 |  | 575 | descriptive | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.gold_recall_raw | 0.5791 |  | 575 | descriptive | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05 |
| audit.discoverybench.null_hit_rate_bh | 0.0012 |  | 5031 | synthetic | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05; target permuted, numpy default_rng(seed 20261117 + task index) |
| audit.discoverybench.null_hit_rate_raw | 0.0473 |  | 5031 | synthetic | fetch:discoverybench |  | per column vs target: Spearman (numeric), point-biserial (binary-numeric), Kruskal-Wallis (categorical-numeric), chi-square (categorical pairs); BH within task; alpha 0.05; target permuted, numpy default_rng(seed 20261117 + task index) |
| audit.discoverybench.null_tasks_any_hit_bh | 0.0382 |  | 157 | synthetic | fetch:discoverybench |  |  |
| audit.discoverybench.null_tasks_any_hit_raw | 0.7325 |  | 157 | synthetic | fetch:discoverybench |  |  |
| audit.discoverybench.tasks_scanned | 157 |  | 903 | descriptive | fetch:discoverybench | (tasks) |  |
| audit.discoverybench.tasks_total | 903 |  | 903 | descriptive | fetch:discoverybench | (tasks) |  |
| audit.discoverybench.tasks_with_distractor_hit_bh | 0.3885 |  | 157 | descriptive | fetch:discoverybench |  |  |
| audit.discoverybench.tasks_with_distractor_hit_raw | 0.7516 |  | 157 | descriptive | fetch:discoverybench |  |  |
| audit.heldout.h1.mean_agreement_flagged | 0.4408 |  | 38 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) |  | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.mean_agreement_passed | 0.3433 |  | 42 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) |  | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.mwu_p | 0.1431 |  | 80 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) |  | two-sided Mann-Whitney U, unstratified (secondary); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.n_flagged | 38 |  | 80 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) | (runs) | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.n_runs | 80 |  | 80 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) | (runs) | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.no_dev_ideas.perm_p | 0.4878 |  | 20 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) |  | two-sided permutation, labels permuted within idea, 10000 draws, numpy default_rng(20261117); T = mean(passed) - mean(flagged); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.no_dev_ideas.t_difference | -0.2161 |  | 20 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) |  | two-sided permutation, labels permuted within idea, 10000 draws, numpy default_rng(20261117); T = mean(passed) - mean(flagged); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.perm_p | 0.0845 |  | 80 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) |  | two-sided permutation, labels permuted within idea, 10000 draws, numpy default_rng(20261117); T = mean(passed) - mean(flagged); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.rank_biserial | -0.1861 |  | 80 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) |  | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.supported | 0 |  | 80 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) | (1 = yes, 0 = no) | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h1.t_difference | -0.0975 |  | 80 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis) | mean agreement of passed runs minus flagged runs (H1 predicts > 0) | two-sided permutation, labels permuted within idea, 10000 draws, numpy default_rng(20261117); T = mean(passed) - mean(flagged); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h2.mean_soundness_flagged | 0.6296 |  | 9 | exploratory | fetch:codescientist (reviews) + fetch:codescientist-example-experiments |  | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h2.mean_soundness_passed | 0.6667 |  | 11 | exploratory | fetch:codescientist (reviews) + fetch:codescientist-example-experiments |  | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h2.mwu_p | 0.8061 |  | 20 | exploratory | fetch:codescientist (reviews) + fetch:codescientist-example-experiments |  | two-sided Mann-Whitney U (secondary); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h2.n_flagged | 9 |  | 20 | exploratory | fetch:codescientist (reviews) + fetch:codescientist-example-experiments | (papers) | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h2.n_papers | 20 |  | 20 | exploratory | fetch:codescientist (reviews) + fetch:codescientist-example-experiments | (papers) | prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h2.perm_p | 0.8561 |  | 20 | exploratory | fetch:codescientist (reviews) + fetch:codescientist-example-experiments |  | two-sided permutation, 10000 draws, numpy default_rng(20261117); T = mean(passed) - mean(flagged); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout.h2.t_difference | 0.037 |  | 20 | exploratory | fetch:codescientist (reviews) + fetch:codescientist-example-experiments |  | two-sided permutation, 10000 draws, numpy default_rng(20261117); T = mean(passed) - mean(flagged); prereg/audit/heldout_prereg.md (commit 3d864413cef102e3136d82af8cc9e0660ae78026) |
| audit.heldout_v2.h1_units.fisher_p | 0.3647 |  | 79 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) |  | two-sided Fisher exact test of the 2 x 2 table; prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h1_units.n_flagged | 37 |  | 79 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | runs with an error-severity check (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h1_units.n_runs | 79 |  | 79 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | v0.1 H1 units with a faithfulness category (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h1_units.perm_p | 0.3663 |  | 79 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) |  | two-sided permutation, labels permuted across runs, 10000 draws, numpy default_rng(20261118); T = share faithful (passed) - share faithful (flagged); prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h1_units.share_faithful_flagged | 0.3784 |  | 37 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | share rated faithful among flagged runs | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h1_units.share_faithful_passed | 0.5 |  | 42 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | share rated faithful among passed runs | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h1_units.t_difference | 0.1216 |  | 79 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | share faithful, passed minus flagged (H3 predicts > 0) | two-sided permutation, labels permuted across runs, 10000 draws, numpy default_rng(20261118); T = share faithful (passed) - share faithful (flagged); prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.code.a2 | 1 |  | 13 | descriptive | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.code.a5 | 2 |  | 13 | descriptive | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.code.a6 | 7 |  | 13 | descriptive | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.code.r1 | 1 |  | 13 | descriptive | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.code.r3 | 1 |  | 13 | descriptive | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.n_flagged | 1 |  | 13 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | runs with an error-severity check (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.n_runs | 13 |  | 13 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | held-out runs (units) (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.no_dev_ideas.n_flagged | 1 |  | 11 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | runs with an error-severity check (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.no_dev_ideas.n_runs | 11 |  | 11 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | held-out runs without dev ideas (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.no_dev_ideas.perm_p | not measured |  | 11 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) |  | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.perm_p | not measured |  | 13 | heldout | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) |  | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.v01_predictor.n_flagged | 1 |  | 13 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | runs with an error-severity check (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.v01_predictor.n_runs | 13 |  | 13 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) | held-out runs, v0.1 predictor (runs) | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.heldout_v2.h3.v01_predictor.perm_p | not measured |  | 13 | exploratory | fetch:codescientist-full50 + fetch:codescientist (metaanalysis bulk TSV faithfullness_category) |  | prereg/audit/heldout_v2_prereg.md (commit 75b85b4b61444f4c001b50a74b867d1d6e4d4828) |
| audit.resistor_table.cells_reproduced | 9 |  | 9 | descriptive | fetch:codescientist-example-experiments | (table cells) |  |

## receipts

| metric | value | 95% CI | n | split | source | what | test / prereg |
|---|---|---|---|---|---|---|---|
| receipts.asta_example.errors | 0 |  | 1 | descriptive | fetch:asta-plugins | (count) |  |
| receipts.asta_example.spans | 1 |  |  | descriptive | fetch:asta-plugins | (count) |  |
| receipts.asta_example.warnings | 0 |  | 1 | descriptive | fetch:asta-plugins | (count) |  |
| receipts.precision.w1_v01 | 0.54 | [0.403989, 0.670303] | 50 | dev | fetch:sciarena-eval+theorizer-paper-data | precision of W1 (rules v0.1): flagged units labelled a true overreach (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w1_v01_sciarena | 0.48 | [0.300313, 0.665015] | 25 | dev | fetch:sciarena-eval | precision of W1 (rules v0.1): flagged units labelled a true overreach, sciarena only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w1_v01_theorizer | 0.6 | [0.407395, 0.765967] | 25 | dev | fetch:theorizer-paper-data | precision of W1 (rules v0.1): flagged units labelled a true overreach, theorizer only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w1_v02 | 0.56 | [0.42306, 0.688378] | 50 | dev | fetch:sciarena-eval+theorizer-paper-data | precision of W1 (rules v0.2): flagged units labelled a true overreach (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w1_v02_sciarena | 0.48 | [0.300313, 0.665015] | 25 | dev | fetch:sciarena-eval | precision of W1 (rules v0.2): flagged units labelled a true overreach, sciarena only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w1_v02_theorizer | 0.64 | [0.445185, 0.797521] | 25 | dev | fetch:theorizer-paper-data | precision of W1 (rules v0.2): flagged units labelled a true overreach, theorizer only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w2_v01 | 0.26 | [0.158715, 0.395532] | 50 | dev | fetch:sciarena-eval+theorizer-paper-data | precision of W2 (rules v0.1): flagged units labelled a true overreach (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w2_v01_sciarena | 0.28 | [0.142839, 0.475766] | 25 | dev | fetch:sciarena-eval | precision of W2 (rules v0.1): flagged units labelled a true overreach, sciarena only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w2_v01_theorizer | 0.24 | [0.114963, 0.434297] | 25 | dev | fetch:theorizer-paper-data | precision of W2 (rules v0.1): flagged units labelled a true overreach, theorizer only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w2_v02 | 0.32 | [0.207582, 0.458103] | 50 | dev | fetch:sciarena-eval+theorizer-paper-data | precision of W2 (rules v0.2): flagged units labelled a true overreach (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w2_v02_sciarena | 0.36 | [0.202479, 0.554815] | 25 | dev | fetch:sciarena-eval | precision of W2 (rules v0.2): flagged units labelled a true overreach, sciarena only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.precision.w2_v02_theorizer | 0.28 | [0.142839, 0.475766] | 25 | dev | fetch:theorizer-paper-data | precision of W2 (rules v0.2): flagged units labelled a true overreach, theorizer only (proportion) | Wilson 95% interval on the labelled sample |
| receipts.sciarena.exploratory.higher_w1_rate_loses | 0.442804 | [0.382734, 0.50414] | 271 | exploratory | fetch:sciarena-eval | share of included votes in which the response with the higher flag rate lost (proportion of included votes) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.exploratory.higher_w1_rate_permutation_p | 0.068293 |  | 271 | exploratory | fetch:sciarena-eval | (p-value) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.exploratory.higher_w1_rate_sign_p | 0.068201 |  | 271 | exploratory | fetch:sciarena-eval | (p-value) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.exploratory.higher_w2_rate_loses | 0.522989 | [0.469071, 0.576511] | 348 | exploratory | fetch:sciarena-eval | share of included votes in which the response with the higher flag rate lost (proportion of included votes) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.exploratory.higher_w2_rate_permutation_p | 0.425857 |  | 348 | exploratory | fetch:sciarena-eval | (p-value) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.exploratory.higher_w2_rate_sign_p | 0.421388 |  | 348 | exploratory | fetch:sciarena-eval | (p-value) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.heldout.higher_flag_rate_loses | 0.500879 | [0.459004, 0.542744] | 569 | heldout | fetch:sciarena-eval | share of included votes in which the response with the higher flag rate lost (proportion of included votes) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.heldout.higher_flag_rate_permutation_p | 1.0 |  | 569 | heldout | fetch:sciarena-eval | (p-value) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.heldout.higher_flag_rate_sign_p | 1.0 |  | 569 | heldout | fetch:sciarena-eval | (p-value) | two-sided exact sign test (binomial, p=0.5) on paired votes, ties and equal rates excluded; permutation null: 10000 sign flips, seed 0; prereg/receipts/sciarena_prereg.md @ adb9f3eedd0c04d98bdd1580df66fd0ae5260bcf |
| receipts.sciarena.listed_cited_rate | 0.999964 | [0.999795, 0.999994] | 27577 | descriptive | fetch:sciarena-eval | listed citations that are cited inline at least once (proportion) |  |
| receipts.sciarena.n_inline_citations | 31820 |  |  | descriptive | fetch:sciarena-eval | (count) |  |
| receipts.sciarena.n_listed_citations | 27577 |  |  | descriptive | fetch:sciarena-eval | (count) |  |
| receipts.sciarena.n_quoted_spans | 10 |  |  | descriptive | fetch:sciarena-eval | (count) |  |
| receipts.sciarena.n_responses_with_citations | 3993 |  | 4000 | descriptive | fetch:sciarena-eval | (count) |  |
| receipts.sciarena.n_votes | 2000 |  |  | descriptive | fetch:sciarena-eval | (count) |  |
| receipts.sciarena.quote_found_rate | 0.2 | [0.056682, 0.509838] | 10 | descriptive | fetch:sciarena-eval | quoted spans found verbatim in a cited passage (proportion) |  |
| receipts.sciarena.resolution_rate | 0.999969 | [0.999822, 0.999994] | 31820 | descriptive | fetch:sciarena-eval | inline citations that resolve to a listed citation with passage text (proportion) |  |
| receipts.sciarena.v02.w1_or_w2_rate | 0.031145 | [0.029292, 0.033111] | 31819 | descriptive | fetch:sciarena-eval | W1 or W2 (rules v0.2) per resolved inline citation (proportion) |  |
| receipts.sciarena.v02.w1_rate | 0.01496 | [0.013683, 0.016353] | 31819 | descriptive | fetch:sciarena-eval | W1 (rules v0.2) per resolved inline citation (proportion) |  |
| receipts.sciarena.v02.w2_rate | 0.0165 | [0.015157, 0.017959] | 31819 | descriptive | fetch:sciarena-eval | W2 (rules v0.2) per resolved inline citation (proportion) |  |
| receipts.sciarena.w1_or_w2_rate | 0.028002 | [0.026246, 0.029873] | 31819 | descriptive | fetch:sciarena-eval | W1 or W2 per resolved inline citation (proportion) |  |
| receipts.sciarena.w1_rate | 0.014205 | [0.012963, 0.015565] | 31819 | descriptive | fetch:sciarena-eval | W1 per resolved inline citation (proportion) |  |
| receipts.sciarena.w2_rate | 0.014017 | [0.012782, 0.015368] | 31819 | descriptive | fetch:sciarena-eval | W2 per resolved inline citation (proportion) |  |
| receipts.seeded.control_false_findings | 0 |  | 14 | synthetic | examples/receipts/seeded | error or warning findings on the clean controls (count) |  |
| receipts.seeded.recall | 1.0 |  | 17 | synthetic | examples/receipts/seeded | planted defects found (exact code, file, line and key) |  |
| receipts.seeded.unexpected_findings | 0 |  | 17 | synthetic | examples/receipts/seeded | error or warning findings not in the expected file (count) |  |
| receipts.theorizer.exploratory.lit_accuracy.t1_diff_high_minus_low_pa | 0.00748 |  | 317 | exploratory | fetch:theorizer-paper-data | share of theories with any T1: high minus low predictive-accuracy support fraction (difference in proportions) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_accuracy.t1_diff_permutation_p | 0.667733 |  | 317 | exploratory | fetch:theorizer-paper-data | (p-value) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_accuracy.t1_rate_high_pa | 0.015544 | [0.0053, 0.044697] | 193 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.exploratory.lit_accuracy.t1_rate_low_pa | 0.008065 | [0.001425, 0.044268] | 124 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.exploratory.lit_accuracy.w1_diff_high_minus_low_pa | -0.038609 |  | 317 | exploratory | fetch:theorizer-paper-data | share of theories with any W1: high minus low predictive-accuracy support fraction (difference in proportions) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_accuracy.w1_diff_permutation_p | 0.147585 |  | 317 | exploratory | fetch:theorizer-paper-data | (p-value) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_accuracy.w1_rate_high_pa | 0.025907 | [0.011115, 0.059202] | 193 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.exploratory.lit_accuracy.w1_rate_low_pa | 0.064516 | [0.033051, 0.122153] | 124 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.exploratory.lit_novelty.t1_diff_high_minus_low_pa | 0.0 |  | 115 | exploratory | fetch:theorizer-paper-data | share of theories with any T1: high minus low predictive-accuracy support fraction (difference in proportions) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_novelty.t1_diff_permutation_p | 1.0 |  | 115 | exploratory | fetch:theorizer-paper-data | (p-value) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_novelty.t1_rate_high_pa | 0.0 | [0.0, 0.061129] | 59 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.exploratory.lit_novelty.t1_rate_low_pa | 0.0 | [0.0, 0.064194] | 56 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.exploratory.lit_novelty.w1_diff_high_minus_low_pa | -0.027542 |  | 115 | exploratory | fetch:theorizer-paper-data | share of theories with any W1: high minus low predictive-accuracy support fraction (difference in proportions) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_novelty.w1_diff_permutation_p | 0.790621 |  | 115 | exploratory | fetch:theorizer-paper-data | (p-value) | two-sided permutation test, 10000 relabellings, seed 0 |
| receipts.theorizer.exploratory.lit_novelty.w1_rate_high_pa | 0.847458 | [0.73482, 0.917615] | 59 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.exploratory.lit_novelty.w1_rate_low_pa | 0.875 | [0.763745, 0.938109] | 56 | exploratory | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_accuracy.t1_rate | 0.016184 | [0.01408, 0.018596] | 12049 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_accuracy.w1_item_rate | 0.007163 | [0.005322, 0.009634] | 6003 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_accuracy.w1_law_rate | 0.002863 | [0.000974, 0.008382] | 1048 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_accuracy.w2_item_rate | 0.025487 | [0.021794, 0.029788] | 6003 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_accuracy.w2_law_rate | 0.0 | [0.0, 0.003652] | 1048 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_novelty.t1_rate | 0.0 | [0.0, 0.001672] | 2294 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_novelty.w1_item_rate | 0.216249 | [0.197189, 0.236608] | 1674 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_novelty.w1_law_rate | 0.846246 | [0.820264, 0.869071] | 839 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_novelty.w2_item_rate | 0.023895 | [0.017596, 0.032373] | 1674 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.lit_novelty.w2_law_rate | 0.002384 | [0.000654, 0.00865] | 839 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.n_evidence_links | 18205 |  |  | descriptive | fetch:theorizer-paper-data | evidence links in law evidence lists, literature conditions (count) |  |
| receipts.theorizer.n_evidence_records | 62093 |  |  | descriptive | fetch:theorizer-paper-data | evidence records (extraction instances) in the results files (count) |  |
| receipts.theorizer.n_evidence_refs | 14343 |  |  | descriptive | fetch:theorizer-paper-data | distinct evidence IDs cited per law (law, ID pairs), literature conditions (count) |  |
| receipts.theorizer.n_extraction_files | 16316 |  |  | descriptive | fetch:theorizer-paper-data | extraction result files (one extraction of one paper each) (count) |  |
| receipts.theorizer.n_laws | 4187 |  |  | descriptive | fetch:theorizer-paper-data | laws (statements) parsed (count) |  |
| receipts.theorizer.n_laws_literature | 1897 |  |  | descriptive | fetch:theorizer-paper-data | laws in the literature-supported conditions (count) |  |
| receipts.theorizer.n_theories | 2856 |  |  | descriptive | fetch:theorizer-paper-data | theory files across the four released conditions (count) |  |
| receipts.theorizer.n_theories_literature | 1338 |  |  | descriptive | fetch:theorizer-paper-data | theories in the two literature-supported conditions (count) |  |
| receipts.theorizer.param_accuracy.t2_rate | 0.024816 | [0.018057, 0.034017] | 1491 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.param_novelty.t2_rate | 0.0 | [0.0, 0.004785] | 799 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.parse_coverage_results_files | 0.808961 | [0.802856, 0.81492] | 16316 | descriptive | fetch:theorizer-paper-data | results files with at least one evidence record parsed (proportion) |  |
| receipts.theorizer.parse_coverage_statements | 1.0 | [0.999083, 1.0] | 4187 | descriptive | fetch:theorizer-paper-data | laws whose statement text parsed (proportion) |  |
| receipts.theorizer.parse_coverage_theories | 1.0 | [0.998657, 1.0] | 2856 | descriptive | fetch:theorizer-paper-data | theory files with at least one law parsed (proportion) |  |
| receipts.theorizer.t1_href_fallback_share | 1.0 | [0.981606, 1.0] | 205 | descriptive | fetch:theorizer-paper-data | T1 links whose href is the export's fallback ../results/<id>.html, which names no extraction file (proportion) |  |
| receipts.theorizer.t1_malformed_ids | 0 |  |  | descriptive | fetch:theorizer-paper-data | T1 links whose ID is not of the form e<n>.<k> (count) |  |
| receipts.theorizer.t1_rate | 0.013595 | [0.011826, 0.015625] | 14343 | descriptive | fetch:theorizer-paper-data | T1: cited evidence IDs that resolve to no evidence record (proportion) |  |
| receipts.theorizer.t1_theory_rate | 0.005232 | [0.002537, 0.01076] | 1338 | descriptive | fetch:theorizer-paper-data | theories with at least one T1 (proportion) |  |
| receipts.theorizer.t2_empty_evidence_rate | 0.008837 | [0.006418, 0.012156] | 4187 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.t2_empty_scope_rate | 0.008837 | [0.006418, 0.012156] | 4187 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.t2_rate | 0.008837 | [0.006418, 0.012156] | 4187 | descriptive | fetch:theorizer-paper-data | T2: laws with an empty scope or an empty evidence list (proportion) |  |
| receipts.theorizer.t2_rate_literature | 0.0 | [0.0, 0.002021] | 1897 | descriptive | fetch:theorizer-paper-data | T2 in the literature-supported conditions (proportion) |  |
| receipts.theorizer.v02.lit_accuracy.w1_item_rate | 0.006663 | [0.004897, 0.00906] | 6003 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.lit_accuracy.w1_law_rate | 0.002863 | [0.000974, 0.008382] | 1048 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.lit_accuracy.w2_item_rate | 0.024654 | [0.021025, 0.028892] | 6003 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.lit_accuracy.w2_law_rate | 0.0 | [0.0, 0.003652] | 1048 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.lit_novelty.w1_item_rate | 0.213859 | [0.194884, 0.234145] | 1674 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.lit_novelty.w1_law_rate | 0.845054 | [0.819001, 0.867961] | 839 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.lit_novelty.w2_item_rate | 0.023895 | [0.017596, 0.032373] | 1674 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.lit_novelty.w2_law_rate | 0.003576 | [0.001217, 0.01046] | 839 | descriptive | fetch:theorizer-paper-data | (proportion) |  |
| receipts.theorizer.v02.w1_item_rate | 0.051843 | [0.047104, 0.057031] | 7677 | descriptive | fetch:theorizer-paper-data | W1 (rules v0.2): a number in an evidence item absent from the records it cites (proportion) |  |
| receipts.theorizer.v02.w1_law_rate | 0.377318 | [0.355719, 0.399417] | 1887 | descriptive | fetch:theorizer-paper-data | W1 (rules v0.2): a number in the law statement absent from its cited records (proportion) |  |
| receipts.theorizer.v02.w2_item_rate | 0.024489 | [0.021262, 0.028191] | 7677 | descriptive | fetch:theorizer-paper-data | W2 (rules v0.2): assertive evidence item over hedged records (proportion) |  |
| receipts.theorizer.v02.w2_law_rate | 0.00159 | [0.000541, 0.004664] | 1887 | descriptive | fetch:theorizer-paper-data | W2 (rules v0.2): assertive law over hedged cited records (proportion) |  |
| receipts.theorizer.w1_item_rate | 0.052755 | [0.047974, 0.057983] | 7677 | descriptive | fetch:theorizer-paper-data | W1: a number in an evidence item absent from the records it cites (proportion) |  |
| receipts.theorizer.w1_law_rate | 0.377848 | [0.356241, 0.399952] | 1887 | descriptive | fetch:theorizer-paper-data | W1: a number in the law statement absent from its cited records (proportion) |  |
| receipts.theorizer.w2_item_rate | 0.02514 | [0.021868, 0.028887] | 7677 | descriptive | fetch:theorizer-paper-data | W2: assertive evidence item over hedged records (proportion) |  |
| receipts.theorizer.w2_law_rate | 0.00106 | [0.000291, 0.003856] | 1887 | descriptive | fetch:theorizer-paper-data | W2: assertive law over hedged cited records (proportion) |  |

## reproduce

| metric | value | 95% CI | n | split | source | what | test / prereg |
|---|---|---|---|---|---|---|---|
| reproduce.cs.agreement_with_run_labels | 0.2769 | [0.1829, 0.3958] | 65 | descriptive | fetch:codescientist+codescientist-full50 | pairs where our V1 verdict matches CodeScientist's judgement of the reproduction run (reproduced~support, not_reproduced~refute, inconclusive~inconclusive) (fraction) | exact agreement |
| reproduce.cs.batch2.completed_runs | 94 |  |  | descriptive | fetch:codescientist+codescientist-full50+codescientist-example-experiments | completed reruns in the batch without expert notes (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.batch2.found_in.codescientist_repository | 0 |  | 250 | descriptive | fetch:codescientist+codescientist-full50+codescientist-example-experiments | of those run directories, present here (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.batch2.found_in.example_experiments_zip | 0 |  | 250 | descriptive | fetch:codescientist+codescientist-full50+codescientist-example-experiments | of those run directories, present here (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.batch2.found_in.full50_zip | 0 |  | 250 | descriptive | fetch:codescientist+codescientist-full50+codescientist-example-experiments | of those run directories, present here (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.batch2.pairs | 60 |  |  | descriptive | fetch:codescientist+codescientist-full50+codescientist-example-experiments | (source, later run) pairs that batch would give (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.batch2.run_directories_named | 250 |  |  | descriptive | fetch:codescientist+codescientist-full50+codescientist-example-experiments | run directories the batch's experiment list names (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.coverage.ambiguous_primary | 15 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.coverage.no_bootstrap_block | 22 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.coverage.recoverable | 24 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.coverage.unreadable_results_file | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.coverage_recoverable | 0.3692 | [0.2623, 0.4908] | 65 | descriptive | fetch:codescientist+codescientist-full50 | pairs whose two runs both give a recoverable primary bootstrap comparison (fraction) |  |
| reproduce.cs.d1.decidable | 9 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.d1.no_data | 41 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.d1.underpowered | 15 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.f1.not_comparable | 10 |  | 24 | descriptive | fetch:codescientist+codescientist-full50 | F1 among recoverable pairs (count) |  |
| reproduce.cs.f1.proxy | 11 |  | 24 | descriptive | fetch:codescientist+codescientist-full50 | F1 among recoverable pairs (count) |  |
| reproduce.cs.f1.same_quantity | 3 |  | 24 | descriptive | fetch:codescientist+codescientist-full50 | F1 among recoverable pairs (count) |  |
| reproduce.cs.ideas_2plus_runs | 24 |  | 50 | descriptive | fetch:codescientist+codescientist-full50 | ideas with at least 2 completed runs, of the batch's ideas (count) |  |
| reproduce.cs.outcome.supported | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.outcome.undecided-misses_threshold | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.outcome.undecided-no_data | 41 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.outcome.undecided-no_positive_control | 1 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.outcome.undecided-not_comparable | 10 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.outcome.undecided-underpowered | 7 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.p2_verbatim | 1 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | pairs whose two runs state the hypothesis in identical words (count) |  |
| reproduce.cs.pairs | 65 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (source run, later run) pairs from ideas with at least 2 completed runs (count) |  |
| reproduce.cs.reproduced_source_sign.negative | 2 |  | 4 | descriptive | fetch:codescientist+codescientist-full50 | v0.1 reproduced pairs by the sign of the source run's own mean difference (added in v0.2 as a check) (count) |  |
| reproduce.cs.reproduced_source_sign.positive | 2 |  | 4 | descriptive | fetch:codescientist+codescientist-full50 | v0.1 reproduced pairs by the sign of the source run's own mean difference (added in v0.2 as a check) (count) |  |
| reproduce.cs.reproduced_source_sign.zero | 0 |  | 4 | descriptive | fetch:codescientist+codescientist-full50 | v0.1 reproduced pairs by the sign of the source run's own mean difference (added in v0.2 as a check) (count) |  |
| reproduce.cs.v0_2.agreement_with_run_labels | 0.2769 | [0.1829, 0.3958] | 65 | descriptive | fetch:codescientist+codescientist-full50 | pairs where our V1 verdict matches CodeScientist's judgement of the reproduction run (fraction) | exact agreement; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.coverage.ambiguous_primary | 15 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.coverage.no_test_output | 14 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.coverage.recoverable | 32 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.coverage.test_output_incomplete | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.coverage_recoverable | 0.4923 | [0.3746, 0.6108] | 65 | descriptive | fetch:codescientist+codescientist-full50 | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.d1.decidable | 14 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.d1.no_data | 33 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.d1.underpowered | 18 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.outcome.supported | 6 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.outcome.undecided-misses_threshold | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.outcome.undecided-no_data | 33 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.outcome.undecided-no_positive_control | 3 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.outcome.undecided-not_comparable | 11 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.outcome.undecided-underpowered | 10 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.per_comparison.n | 6 |  |  | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.per_comparison.v1.inconclusive | 6 |  | 6 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.per_comparison.v1.not_reproduced | 0 |  | 6 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.per_comparison.v1.reproduced | 0 |  | 6 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.v1.inconclusive | 59 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.as_preregistered.v1.reproduced | 6 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.coverage.ambiguous_primary | 17 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.coverage.no_test_output | 14 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.coverage.recoverable | 30 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.coverage.test_output_incomplete | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.coverage_recoverable | 0.4615 | [0.3459, 0.5815] | 65 | descriptive | fetch:codescientist+codescientist-full50 | pairs whose two runs both give a primary bootstrap comparison under the v0.2 rule (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.d1.decidable | 10 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.d1.no_data | 35 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.d1.uncheckable | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.d1.underpowered | 18 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.agreement_with_run_labels | 0.2769 | [0.1829, 0.3958] | 65 | descriptive | fetch:codescientist+codescientist-full50 | (fraction) | exact agreement; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.outcome.supported | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.outcome.undecided-misses_threshold | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.outcome.undecided-no_data | 35 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.outcome.undecided-no_positive_control | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.outcome.undecided-not_comparable | 11 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.outcome.undecided-uncheckable | 1 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.outcome.undecided-underpowered | 10 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.per_comparison.v1.inconclusive | 14 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.per_comparison.v1.not_reproduced | 0 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.per_comparison.v1.reproduced | 3 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.v1.inconclusive | 61 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.extraction_only.v1.reproduced | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.f1.not_comparable | 11 |  | 30 | descriptive | fetch:codescientist+codescientist-full50 | F1 among recoverable pairs (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.f1.proxy | 15 |  | 30 | descriptive | fetch:codescientist+codescientist-full50 | F1 among recoverable pairs (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.f1.same_quantity | 4 |  | 30 | descriptive | fetch:codescientist+codescientist-full50 | F1 among recoverable pairs (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.newly_recoverable | 6 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | pairs recoverable under v0.2 and not under v0.1 (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.opposite_effect | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.supported | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.undecided-misses_threshold | 1 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.undecided-no_data | 35 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.undecided-no_positive_control | 3 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.undecided-not_comparable | 11 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.undecided-source_null | 7 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.outcome.undecided-underpowered | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.n | 17 |  |  | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.outcome.opposite_effect | 4 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.outcome.supported | 6 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.outcome.undecided-no_positive_control | 1 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.outcome.undecided-not_comparable | 3 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.outcome.undecided-source_null | 2 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.outcome.undecided-underpowered | 1 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.pairs | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | pairs contributing at least one matched comparison (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.reproduced_source_sign.negative | 6 |  | 6 | descriptive | fetch:codescientist+codescientist-full50 | reproduced comparisons by the sign of the source run's own mean difference (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.reproduced_source_sign.positive | 0 |  | 6 | descriptive | fetch:codescientist+codescientist-full50 | reproduced comparisons by the sign of the source run's own mean difference (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.reproduced_source_sign.zero | 0 |  | 6 | descriptive | fetch:codescientist+codescientist-full50 | reproduced comparisons by the sign of the source run's own mean difference (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.v1.inconclusive | 7 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.v1.not_reproduced | 4 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.per_comparison.v1.reproduced | 6 |  | 17 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.reproduced_source_sign.negative | 0 |  | 2 | descriptive | fetch:codescientist+codescientist-full50 | reproduced pairs by the sign of the source run's own mean difference (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.reproduced_source_sign.positive | 2 |  | 2 | descriptive | fetch:codescientist+codescientist-full50 | reproduced pairs by the sign of the source run's own mean difference (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.reproduced_source_sign.zero | 0 |  | 2 | descriptive | fetch:codescientist+codescientist-full50 | reproduced pairs by the sign of the source run's own mean difference (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs | 103 |  |  | descriptive | fetch:codescientist+codescientist-full50 | completed runs of the ideas read (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.files_repaired | 0 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | output files that parsed only with the restricted literal reader (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.ok_by.log.json.experiment_plan | 1 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | readable runs by tier and basis of the primary (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.ok_by.log.json.single | 4 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | readable runs by tier and basis of the primary (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.ok_by.results.json.hypothesis | 2 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | readable runs by tier and basis of the primary (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.ok_by.results.json.single | 47 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | readable runs by tier and basis of the primary (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.ok_by.to_save.hypothesis | 1 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | readable runs by tier and basis of the primary (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.ok_by.to_save.single | 6 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | readable runs by tier and basis of the primary (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.status.ambiguous_primary | 18 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.status.no_test_output | 22 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.status.ok | 61 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.runs.status.test_output_incomplete | 2 |  | 103 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.transition.inconclusive.to_inconclusive | 61 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | v0.1 verdict to v0.2 verdict, per pair (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.transition.reproduced.to_not_reproduced | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | v0.1 verdict to v0.2 verdict, per pair (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.transition.reproduced.to_reproduced | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | v0.1 verdict to v0.2 verdict, per pair (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.v1.inconclusive | 61 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.v1.not_reproduced | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.v1.reproduced | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.vs_labels.ours_inconclusive.theirs_inconclusive | 16 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.vs_labels.ours_inconclusive.theirs_refute | 20 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.vs_labels.ours_inconclusive.theirs_support | 25 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.vs_labels.ours_not_reproduced.theirs_inconclusive | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v0_2.vs_labels.ours_reproduced.theirs_support | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.cs.v1.inconclusive | 61 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.v1.reproduced | 4 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.vs_consistency.their_judgements_different.ours_inconclusive | 38 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | their judgements of the two runs of a pair (same or different) beside our V1 verdict for the pair (count) |  |
| reproduce.cs.vs_consistency.their_judgements_different.ours_reproduced | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | their judgements of the two runs of a pair (same or different) beside our V1 verdict for the pair (count) |  |
| reproduce.cs.vs_consistency.their_judgements_same.ours_inconclusive | 23 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | their judgements of the two runs of a pair (same or different) beside our V1 verdict for the pair (count) |  |
| reproduce.cs.vs_consistency.their_judgements_same.ours_reproduced | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | their judgements of the two runs of a pair (same or different) beside our V1 verdict for the pair (count) |  |
| reproduce.cs.vs_labels.ours_inconclusive.theirs_inconclusive | 16 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.vs_labels.ours_inconclusive.theirs_refute | 20 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.vs_labels.ours_inconclusive.theirs_support | 25 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.vs_labels.ours_reproduced.theirs_inconclusive | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.cs.vs_labels.ours_reproduced.theirs_support | 2 |  | 65 | descriptive | fetch:codescientist+codescientist-full50 | (count) |  |
| reproduce.db.null.decidable_reproduced_rate | 0.7609 | [0.6206, 0.8609] | 46 | synthetic | fetch:discoverybench | among pairs D1 classes decidable (fraction) |  |
| reproduce.db.null.full_data_significant | 122 |  | 1569 | synthetic | fetch:discoverybench | pairs with p < 0.05 on all rows (count) |  |
| reproduce.db.null.inconclusive | 1527 |  | 1569 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.not_reproduced | 7 |  | 1569 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.not_reproduced_or_inconclusive_rate | 0.9777 | [0.9691, 0.9839] | 1569 | synthetic | fetch:discoverybench | (fraction) |  |
| reproduce.db.null.outcome.rejected | 7 |  | 1569 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.outcome.supported | 35 |  | 1569 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.outcome.undecided-misses_threshold | 4 |  | 1569 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.outcome.undecided-underpowered | 1523 |  | 1569 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.reproduced | 35 |  | 1569 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.reproduced_and_full_data_significant | 35 |  | 35 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.null.reproduced_rate | 0.0223 | [0.0161, 0.0309] | 1569 | synthetic | fetch:discoverybench | (fraction) |  |
| reproduce.db.null.small_d1_agrees_with_empirical_power | 0.9986 | [0.9949, 0.9996] | 1430 | synthetic | fetch:discoverybench | D1 class at 10 rows vs empirical power from 200 subsamples (>= 0.8 means decidable) (fraction) | exact agreement |
| reproduce.db.null.small_underpowered_rate | 0.9972 | [0.9928, 0.9989] | 1430 | synthetic | fetch:discoverybench | reproductions on 10 rows classed underpowered (fraction) |  |
| reproduce.db.null.source_significant_reproduced_rate | 0.2778 | [0.207, 0.3617] | 126 | synthetic | fetch:discoverybench | among pairs whose source half has p < alpha (fraction) |  |
| reproduce.db.planted.decidable_reproduced_rate | 0.9661 | [0.928, 0.9844] | 177 | synthetic | fetch:discoverybench | among pairs D1 classes decidable (fraction) |  |
| reproduce.db.planted.full_data_significant | 211 |  | 358 | synthetic | fetch:discoverybench | pairs with p < 0.05 on all rows (count) |  |
| reproduce.db.planted.inconclusive | 185 |  | 358 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.not_reproduced | 2 |  | 358 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.outcome.rejected | 2 |  | 358 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.outcome.supported | 171 |  | 358 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.outcome.undecided-misses_threshold | 4 |  | 358 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.outcome.undecided-underpowered | 181 |  | 358 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.reproduced | 171 |  | 358 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.reproduced_and_full_data_significant | 171 |  | 171 | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.planted.reproduced_rate | 0.4777 | [0.4264, 0.5294] | 358 | synthetic | fetch:discoverybench | (fraction) |  |
| reproduce.db.planted.small_d1_agrees_with_empirical_power | 0.9664 | [0.9408, 0.9811] | 327 | synthetic | fetch:discoverybench | D1 class at 10 rows vs empirical power from 200 subsamples (>= 0.8 means decidable) (fraction) | exact agreement |
| reproduce.db.planted.small_underpowered_rate | 0.8502 | [0.8074, 0.8848] | 327 | synthetic | fetch:discoverybench | reproductions on 10 rows classed underpowered (fraction) |  |
| reproduce.db.planted.source_significant_reproduced_rate | 0.8814 | [0.8284, 0.9197] | 194 | synthetic | fetch:discoverybench | among pairs whose source half has p < alpha (fraction) |  |
| reproduce.db.queries_usable | 183 |  | 903 | synthetic | fetch:discoverybench | queries with a target column and a gold expression (count) |  |
| reproduce.db.tasks | 374 |  |  | synthetic | fetch:discoverybench | (count) |  |
| reproduce.db.v0_2.derived.decidable_reproduced_rate | 0.9286 | [0.7735, 0.9802] | 28 | synthetic | fetch:discoverybench | among pairs D1 classes decidable (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.detected_b.mi | 0.3298 | [0.2431, 0.4299] | 94 | synthetic | fetch:discoverybench | pairs whose half-B mi test has p < 0.05 (fraction) | binned mutual information, 199 permutations; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.detected_b.mi_not_pearson | 3 |  | 94 | synthetic | fetch:discoverybench | detected by MI, missed by Pearson, on half B (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.detected_b.pearson | 0.3617 | [0.2718, 0.4625] | 94 | synthetic | fetch:discoverybench | pairs whose half-B pearson test has p < 0.05 (fraction) | Pearson r, two-sided; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.detected_b.spearman | 0.383 | [0.2911, 0.484] | 94 | synthetic | fetch:discoverybench | pairs whose half-B spearman test has p < 0.05 (fraction) | Spearman rho, two-sided; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.inconclusive | 68 |  | 94 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.not_reproduced | 0 |  | 94 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.outcome.supported | 26 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.outcome.undecided-misses_threshold | 2 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.outcome.undecided-source_null | 61 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.outcome.undecided-underpowered | 5 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.reproduced | 26 |  | 94 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.reproduced_rate | 0.2766 | [0.1963, 0.3744] | 94 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.decidable_reproduced_rate | 0.9677 | [0.8381, 0.9943] | 31 | synthetic | fetch:discoverybench | among Spearman records D1 classes decidable (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.inconclusive | 64 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.not_reproduced | 0 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.outcome.supported | 30 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.outcome.undecided-no_positive_control | 1 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.outcome.undecided-source_null | 56 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.outcome.undecided-underpowered | 7 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.reproduced | 30 |  | 94 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.reproduced_rate | 0.3191 | [0.2336, 0.4189] | 94 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived.spearman.underpowered_rate | 0.6702 | [0.5701, 0.7569] | 94 | synthetic | fetch:discoverybench | Spearman records D1 classes underpowered (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived_named.0 | 90 |  | 520 | synthetic | fetch:discoverybench | prose gold hypotheses naming 0 columns (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived_named.1 | 117 |  | 520 | synthetic | fetch:discoverybench | prose gold hypotheses naming 1 columns (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived_named.2 | 127 |  | 520 | synthetic | fetch:discoverybench | prose gold hypotheses naming 2 columns (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived_named.3 | 186 |  | 520 | synthetic | fetch:discoverybench | prose gold hypotheses naming 3+ columns (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived_skipped.already_planted_or_repeated | 0 |  | 127 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived_skipped.constant_in_a_half | 0 |  | 127 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.derived_skipped.not_numeric | 33 |  | 127 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.detected_b.mi | 0.0797 | [0.0673, 0.0941] | 1569 | synthetic | fetch:discoverybench | pairs whose half-B mi test has p < 0.05 (fraction) | binned mutual information, 199 permutations; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.detected_b.mi_not_pearson | 63 |  | 1569 | synthetic | fetch:discoverybench | detected by MI, missed by Pearson, on half B (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.detected_b.pearson | 0.0841 | [0.0714, 0.0989] | 1569 | synthetic | fetch:discoverybench | pairs whose half-B pearson test has p < 0.05 (fraction) | Pearson r, two-sided; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.detected_b.spearman | 0.0873 | [0.0743, 0.1023] | 1569 | synthetic | fetch:discoverybench | pairs whose half-B spearman test has p < 0.05 (fraction) | Spearman rho, two-sided; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.decidable_reproduced_rate | 0.7609 | [0.6206, 0.8609] | 46 | synthetic | fetch:discoverybench | among pairs D1 classes decidable (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.inconclusive | 1527 |  | 1569 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.not_reproduced | 7 |  | 1569 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.not_reproduced_or_inconclusive_rate | 0.9777 | [0.9691, 0.9839] | 1569 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.outcome.rejected | 7 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.outcome.supported | 35 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.outcome.undecided-misses_threshold | 4 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.outcome.undecided-source_null | 1443 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.outcome.undecided-underpowered | 80 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.reproduced | 35 |  | 1569 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.pearson.reproduced_rate | 0.0223 | [0.0161, 0.0309] | 1569 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.decidable_reproduced_rate | 0.8125 | [0.6806, 0.8981] | 48 | synthetic | fetch:discoverybench | among Spearman records D1 classes decidable (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.inconclusive | 1523 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.not_reproduced | 7 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.not_reproduced_or_inconclusive_rate | 0.9751 | [0.9662, 0.9818] | 1569 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.outcome.rejected | 7 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.outcome.supported | 39 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.outcome.undecided-misses_threshold | 2 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.outcome.undecided-source_null | 1446 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.outcome.undecided-underpowered | 75 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.reproduced | 39 |  | 1569 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.reproduced_rate | 0.0249 | [0.0182, 0.0338] | 1569 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.null.spearman.underpowered_rate | 0.9688 | [0.959, 0.9763] | 1569 | synthetic | fetch:discoverybench | Spearman records D1 classes underpowered (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.detected_b.mi | 0.5503 | [0.4985, 0.601] | 358 | synthetic | fetch:discoverybench | pairs whose half-B mi test has p < 0.05 (fraction) | binned mutual information, 199 permutations; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.detected_b.mi_not_pearson | 29 |  | 358 | synthetic | fetch:discoverybench | detected by MI, missed by Pearson, on half B (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.detected_b.pearson | 0.5363 | [0.4845, 0.5873] | 358 | synthetic | fetch:discoverybench | pairs whose half-B pearson test has p < 0.05 (fraction) | Pearson r, two-sided; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.detected_b.spearman | 0.5475 | [0.4957, 0.5983] | 358 | synthetic | fetch:discoverybench | pairs whose half-B spearman test has p < 0.05 (fraction) | Spearman rho, two-sided; prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.decidable_reproduced_rate | 0.9661 | [0.928, 0.9844] | 177 | synthetic | fetch:discoverybench | among pairs D1 classes decidable (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.inconclusive | 185 |  | 358 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.not_reproduced | 2 |  | 358 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.outcome.rejected | 2 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.outcome.supported | 171 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.outcome.undecided-misses_threshold | 4 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.outcome.undecided-source_null | 164 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.outcome.undecided-underpowered | 17 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.reproduced | 171 |  | 358 | synthetic | fetch:discoverybench | Pearson verdict under the v0.2 verdict rule (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.pearson.reproduced_rate | 0.4777 | [0.4264, 0.5294] | 358 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.decidable_reproduced_rate | 0.9827 | [0.9503, 0.9941] | 173 | synthetic | fetch:discoverybench | among Spearman records D1 classes decidable (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.inconclusive | 186 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.not_reproduced | 2 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.outcome.rejected | 2 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.outcome.supported | 170 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.outcome.undecided-misses_threshold | 1 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.outcome.undecided-source_null | 162 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.outcome.undecided-underpowered | 23 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.reproduced | 170 |  | 358 | synthetic | fetch:discoverybench | (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.reproduced_rate | 0.4749 | [0.4237, 0.5266] | 358 | synthetic | fetch:discoverybench | (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.planted.spearman.underpowered_rate | 0.5168 | [0.4651, 0.5681] | 358 | synthetic | fetch:discoverybench | Spearman records D1 classes underpowered (fraction) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.queries_gold_text_only | 520 |  | 903 | synthetic | fetch:discoverybench | queries with a prose gold hypothesis and no gold expression (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
| reproduce.db.v0_2.queries_no_gold | 200 |  | 903 | synthetic | fetch:discoverybench | queries with neither (count) | prereg/reproduce/cs_extraction_v0_2.md @ 0df1320 |
