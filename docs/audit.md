# C2 Experiment audit (`consilience-ai2 audit`)

A deterministic, receipt-backed audit of agent-run experiments (rules v0.2,
`audit-rules-2`). It reads AutoDiscovery
runs and CodeScientist experiment directories in their native formats and runs fixed rules
over each experiment ("node"). It is built to run **beside** AutoDiscovery's "Validity
Check", which is one language-model prompt returning `{feedback, success}`: that text is
hashed and kept next to each verdict, never judged, and the audit never calls a model.
The same input gives byte-identical output.

Every number below renders from `results/audit.json` (written by
`analyses/audit/run_all.py`) or is a fixed rule constant listed in
`scripts/numbers_allowlist/audit.txt`.

## Use

```bash
consilience-ai2 audit run <out_dir> [--format autodiscovery|codescientist] \
                                    [--metadata dataset_metadata.json] [--json OUT]
```

- An AutoDiscovery `--out_dir` (`mcts_node_<level>_<idx>.json`, else `mcts_nodes_all.json`,
  else `mcts_nodes.json`; plus `args.json`), or a hosted run's `results.json` from
  `asta autodiscovery results <run_id> -o results.json`. The dataset metadata (the file
  given to `--dataset_metadata`) is read from `args.json` when it resolves, or from
  `--metadata`; without it A3 is not checked. Level-0/1 nodes and nodes with no
  hypothesis hold no experiment and are skipped, as asta-plugins' `runlog.py` does.
- A CodeScientist experiment directory (`history.json`, `modal-python-<ts>/`,
  `report/report.tex`), or a directory of them. The last `modal-python-*` directory is the
  run behind the report: its `main.py` is the code and its `modal-output/` (stdout,
  `log.json`, `results.json`) is the evidence. The claim is the report (else
  `report-watermarked/report.tex`, else the summary in `history.json`). Zip archives are
  read in place (`Tree(zf=..., prefix=...)`).

It writes `validity_audit.json` (default `<out_dir>/validity_audit.json`), prints one line
per node (`<id>: pass|flag(warning)|flag(error)|refuse q=<q> <codes>`) and GitHub annotation
lines for errors and warnings. Exit 0 when no node has an error-severity finding, 1 otherwise or on
unreadable input, 2 on a usage error. Python API:
`consilience_ai2.audit.audit_path(path, format=None, metadata=None)`.

**Hooks.** The post-run command above needs no change to AutoDiscovery. An in-run example,
`examples/audit/run_with_audit.py`, wraps `autodiscovery.mcts_utils.save_nodes` from
outside (the `run_relaxed.py` pattern) and adds a `deterministic_checks` field to each node
dict before the nodes are saved. It is an example only, not a patch to Ai2's code, and it
was exercised only against the synthetic fixtures. The Claude Code plugin
`plugins/consilience-audit` (skill `experiment-audit`) runs the CLI and reads the receipts.

## Fields read

| Kind | AutoDiscovery | CodeScientist |
|---|---|---|
| claim | `analysis`; `review` when the reviewer passed the node | the report (or the run summary) |
| context | `hypothesis`, `experiment_plan` | — |
| evidence | `code_output` | stdout, `log.json`, `results.json` of the final run |
| code | `code` | `main.py` of the final run |
| beliefs | `surprising`, `prior.mean`, `posterior.mean` | — (every reported experiment is a candidate finding) |

For a field inside a JSON file the receipt source is `<file>#<field>` and the offsets and
line count inside the field's decoded text. A LaTeX report's preamble, figure and table
options, labels, references and comments are masked and never read as claims.

## Checks (rules v0.2, `audit-rules-2`)

The rules have versions. **v0.2** (`audit-rules-2`, this section) is what the CLI runs.
**v0.1** (`audit-rules-1`, git tree `cca16a0` of `consilience_ai2/audit`, commit d24d2f7) is
the version the published development and held-out results were scored with; those results
are kept as they were and are recomputed from that frozen tree, never re-scored with v0.2
(`analyses/audit/rules_versions.py`). What changed and why is listed after the table.

Severities are fixed by what a reviewer would do with the finding. **Errors** are reserved
for things a reviewer rejects a result for: a number in the write-up that is in no output,
a random-only baseline, a hard-coded result, a column that does not exist, "significant"
with no test, reruns that mostly fail to support the result, and (R5) a component that
reaches no output. **Warnings** are things a reviewer would ask about. **Info notes** on
reporting conventions (A7) are kept in the output but never flag.

**Verdict mapping (explicit, `verdict_level`).** `refuse`: U1, nothing can be checked.
`flag(error)`: at least one other error. `flag(warning)`: warnings only. `pass`: no error or
warning (info only). "Pass" means no rule fired, not that a finding is true. `verdict` keeps
the three-way value (`pass`, `flag`, `refuse`). A check that cannot apply to a node is listed
in `not_applicable`.

| Code | Severity | Rule (exact) |
|---|---|---|
| U1 | error (refuse) | Uncheckable: the node has no evidence text, or no claim text. |
| A1 | error / warning | Every decimal or percentage in a claim field appears in the evidence (any number printed anywhere in the output or results files), in a code literal, or in the plan, at the printed precision (`core.numbers.agrees_at_printed_precision`; half-up or half-even; absolute values; also x100 and /100, so a printed percentage matches a printed fraction), or is **derived**: a ratio, relative change or difference of two other numbers of the same sentence that are themselves supported, with change wording within 40 characters ("a 76% increase"). Those pass (info, with the derivation in `derived_from`). **Warning:** the number agrees with a printed number that has at least 3 significant digits and one decimal place fewer (`tier: coarser_precision`: the write-up gives one more digit than the run printed), or it is in no text output while the code writes formatted values into figure text and saves figures (`tier: figure_only`: the number may be printed only in a figure, which the audit cannot read). **Error:** in none of these (`tier: absent`). Integers are not checked here (A2 covers sample sizes). Bounds (`<`, `>`, "less than", "at least", "over"...) and ambiguous separators are skipped and counted. |
| A2 | warning | A stated n (`n = 50`, `N: 50`, or `<k> <unit>` with k of at least 5 from a fixed unit list: episodes, games, samples, participants, ...) in a claim or the plan must be printed (the same patterns in the output, sample-size keys in `results.json`, or a list length) or be an integer n constant in the code (a name like `N_EPISODES`, `num_samples`, a `{"PILOT": 25}` entry, a `range(N)` bound). Bounded mentions ("over 600") and mentions next to "bootstrap", "resample", "permutation", "iteration" or "steps" are skipped. |
| A3 | error (code) / warning (hypothesis) | A column the code reads from a data frame (`df["x"]`, `df[["a","b"]]`, `df.loc[:, "x"]`, `groupby("x")`, `dropna(subset=...)`, formula strings `"y ~ x"`), or a backticked or snake_case name in the hypothesis, is not a dataset column (exact or case-insensitive). Columns the code creates (assigned, `assign`, `rename`, named aggregations, `get_dummies` prefixes) are excluded. Frames are tracked through `read_*`, `DataFrame(...)`, row and column selections and frame-preserving methods; a `groupby` result is not a frame. Needs the dataset metadata. |
| A4 | error | "significant(ly)" or "surprising" in a claim, or a node marked surprising, with no test statistic or p value printed in the evidence (fixed patterns: `p = `, `t(df) =`, `chi-square`, `F(a, b) =`, `U =`, `mannwhitney`, `ttest`, `pearsonr`, `bootstrap`, a p-value key in `results.json`, ...). |
| A5 | warning | Benjamini–Hochberg across every distinct p value parsed from every node of the run (the family). Each node gets q = the smallest BH-adjusted q among its p values. A surprising node (or, without beliefs, a node claiming significance) that is not a null is flagged when q > 0.05. `p < 0.001` is kept as 0.001 (conservative); a printed 0 is kept as 0. Parse coverage (nodes with a p value / checkable nodes) is reported in `parse_coverage`. |
| A6 | warning | A surprising null is paired with its minimum detectable effect. A null is a surprising node whose posterior mean is below its prior mean with no parsed p below 0.05 (AutoDiscovery), or a null claim in the headline (a report's abstract) of a CodeScientist experiment. MDE: d = (z<sub>0.975</sub> + z<sub>0.80</sub>) · sqrt(2 / n) and r = tanh((z<sub>0.975</sub> + z<sub>0.80</sub>) / sqrt(n − 3)). Flagged when d > 0.5 (only effects larger than medium were detectable at 80% power) or n is unknown. |
| A7 | info (note) | A node that claims an effect (surprising, or "significant", "outperforms", "improves", "higher", "correlated", ...) reports no effect size anywhere (Cohen's d, Hedges' g, r, rho, tau, beta, odds or hazard ratio, AUC, eta squared, Cramér's V, R squared, "difference of x", or an effect-size key in `results.json`). A test statistic alone is not an effect size. An info finding with `details.status = "not_reported"`, listed in the node's `notes`; it never flags. |
| R1 | error | Random-only comparator: in sentences of a claim that compare (vs, versus, compared to, against, outperforms, than, over, baseline, control), a random or chance comparator is named ("random baseline/agent/policy/exploration...", "chance", "than random"), and no other comparator is: no plain "baseline"/"control" (not preceded by random, chance, additional, stronger, other...), no "X and random" coordination, no "three/four ... agents/conditions/methods". Sentences with future or modal words (should, could, future, need) are ignored. A random or chance comparator with a limiting or negative word in the 30 characters before it (only, barely, slightly, marginally, no, not, near, close to, comparable, similar...; or "at", "around" right before it) is a limiting statement ("only slightly better than random"), not a claim that rests on beating a random baseline, and does not count (info). |
| R2 | error / warning | Rerun instability: given the verdict labels of reruns of the same idea, support and refute both occur. **Error** when refutes are at least as many as supports (the result does not replicate), **warning** when supports are the majority. Needs rerun labels (CodeScientist: the meta-analysis per-run judgements); not applicable otherwise. |
| R3 | warning | A positive claim (not a null; nulls go to A6) rests on n below the floor of 25 per group: the n for 80% power to detect a large effect (d = 0.8) with a two-sided test at alpha 0.05, `ceil(2 (z_0.975 + z_0.80)^2 / d^2)`. n is the largest n printed (else stated, else a code constant), treated as the per-group n, which is generous to the experiment. |
| R4 | error | A reported decimal or percentage equals a numeric literal with at least two significant digits written in the code on the output path: an argument of a print/log/write/dump call, a constant assigned to a result-like name (accuracy, score, mean, rate, p value, ...), a result-like dict entry, or a constant returned by a result-like function. |
| R5 | error | Built-but-unused, by static analysis (Python `ast`, no execution): a top-level function or class that is used somewhere, does not itself print or save, is not the entry point, and is not in the backward slice of any output sink (print, logging calls, `write`, `json.dump`, `savefig`, `to_csv`, ...). The slice is flow-insensitive and over-approximate: attributes and subscripts collapse to their base name, branch conditions count as dependencies, an argument may be changed by any library call, and by a user function only if that function may mutate the parameter (a store into it, a method call outside a fixed non-mutating list, passing it on, or aliasing it). So a flagged component reaches no output on any path, except through dynamic features; code using `eval`, `exec`, `globals`, `setattr` or a computed `getattr` is reported as not decidable instead. **Scope:** any printed or saved output, not the headline metric. A component whose results are logged anywhere is "used" even if the reported metric ignores it. |

Rule constants: alpha 0.05 (two-sided), power 0.80, R3 effect d = 0.8, A6 bound d = 0.5, A5
threshold q = 0.05 (`consilience_ai2/audit/stats.py`); A1 coarser-precision floor of 3
significant digits and derivation window of 40 characters (`checks.py`).

### What changed from v0.1, and why

v0.1 put error-level flags on 3 of the 6 accepted discoveries of the development set, and
its warning-level A7 fired on 16 of 19, so `pass` almost never happened. v0.2 recalibrates
severities on one principle (an error is what a reviewer would reject a result for; a
missing reporting convention is not) and fixes the parser bugs found by inspecting each
error on an accepted discovery. The thresholds were set from that principle, not by
searching for the rule that fits the 19 labels best; they were still set by people who had
seen these cases, so the v0.2 development numbers are not blind either.

| Rule | v0.1 | v0.2 | Reason |
|---|---|---|---|
| verdict | refuse on U1, A1 or A3 errors | refuse only on U1; other errors flag(error) | An unprinted number or a wrong column is a judged defect, not "cannot check" |
| A1 | error for any number not printed at its precision | error only when absent; derived numbers pass; one-digit-more precision and figure-only numbers warn | Parser bugs: a worded relative change of two printed numbers was flagged (discovery 3); a number written only into a saved figure was called "not printed" (discovery 1). The coarser match needs 3 significant digits so that long logs full of numbers cannot support anything |
| A7 | warning | info note (`not_reported`) | A missing effect size is a reporting convention; CodeScientist reports give group means and a p value but no effect size, and the warning carried no information |
| R1 | any random comparator without another | limiting statements excluded | Parser bug: "only slightly better than random" (discovery 1) is a negative statement, not a random-only baseline |
| R2 | warning on any flip | error when refutes >= supports, warning otherwise | Instability on rerun is a rejection reason when the reruns do not mostly support the result; a minority dissent is mixed evidence |

R5 stays an error although it is not "hard-coded results": a component the reported work
depends on that reaches no output is the defect behind a human rejection in the development
set (discovery 12, "the agents never use the graph they build").

## Output: `validity_audit.json`, version 1

A core report (`version`, `tool`, `tool_version`, `inputs` with SHA-256, `findings`,
`summary`) with the fields of needs-ledger section B.2 beside it:

```json
{"version": 1, "run": "<out_dir or run_id>", "n_nodes": 12, "n_with_pvalue": 10,
 "parse_coverage": {"nodes_with_pvalue": 10, "nodes_checkable": 11, "pvalues": 14, "rate": "..."},
 "rules_version": "audit-rules-2", "rules": {"R5": {"status": "implemented", "severity": "error", "rule": "..."}},
 "verdicts": {"pass": 2, "flag": 9, "refuse": 1},
 "verdict_levels": {"pass": 2, "flag(warning)": 3, "flag(error)": 6, "refuse": 1},
 "verdict_mapping": {"pass": "...", "flag(warning)": "...", "flag(error)": "...", "refuse": "..."},
 "nodes": [{"id": "node_2_1",
            "llm_validity_check": {"success": true, "text_sha256": "..."},
            "checks": [{"code": "A1", "severity": "error", "field": "analysis",
                        "span": "...", "message": "...", "file": "mcts_node_2_1.json",
                        "line": 1, "offset": 24, "end": 28, "sha256": "...",
                        "source": "mcts_node_2_1.json#analysis"}],
            "codes": ["A1"], "notes": [], "not_applicable": ["A6", "R2"], "q_value": "...",
            "verdict": "flag", "verdict_level": "flag(error)"}]}
```

## Validation

### Synthetic AutoDiscovery fixtures (labelled synthetic)

No AutoDiscovery run outputs are public (the search is documented below, under "Real
AutoDiscovery outputs"). `examples/audit/autodiscovery/` holds a
**synthetic** run written by `make_fixtures.py` from the released schema (the keys of
`MCTSNode.to_dict`, `BeliefTrueFalse.DistributionFormat.to_dict`, `ExperimentPlan` and the
hosted `ExperimentModel`, at asta-autodiscovery commit 30e080f): eleven experiment nodes,
one clean, ten each planting one defect (A1 to A7, R1, R4, R5) plus one uncheckable node,
and a hosted `results.json`. The tests assert that the audit finds exactly the planted
codes (under v0.2 the planted A7 defect is found as an info note, not a flag), that the fixture keys equal `MCTSNode.to_dict`'s keys read from the fetched source,
and that the fixtures regenerate byte-identically. True by construction; it shows the
adapter reads the format, not that the rules transfer to real runs.

### Development set: CodeScientist Table 4 (labelled dev, not blind)

The 19 discoveries of the CodeScientist paper's Table 4 (6 accepted, 13 rejected with the
internal reviewer's reason), matched to the 19 corresponding directories of the released
example-experiments archive. **The dev set is not blind.** The v0.1 rules were written
knowing these reasons, and the v0.2 recalibration was decided by people who had inspected
these cases (the false flags on the accepted discoveries in particular), so neither
column below measures generalisation; they measure fit to the cases that motivated the
rules. R2 is given each idea's per-run judgements from the repository's meta-analysis file;
note that the accepted discoveries are follow-on runs, while those judgements are of the
idea's five original runs. Per-discovery codes for both versions are in
`analyses/audit/dev_table.md`. The v0.1 column is recomputed from the frozen v0.1 rules.

| dev, 19 discoveries | v0.1 | v0.2 |
|---|---|---|
| accepted (6) with an error-severity code | 3 | 3 |
| accepted (6) with any error or warning | 6 | 5 |
| rejected (13) with an error-severity code | 6 | 8 |
| rejected (13) with any error or warning | 13 | 12 |
| rejected (13) flagged by a code meant for their reason | 9 | 8 |
| rejected with a deterministic reason (12), same | 9 | 8 |
| discoveries with A7 (no effect size) | 16 flags | 16 info notes |

Confusion matrix, human verdict by audit verdict level (v0.1 levels follow its own mapping,
in which A1 and A3 errors refused):

| dev | pass | flag(warning) | flag(error) | refuse |
|---|---|---|---|---|
| accepted, v0.1 | 0 | 3 | 0 | 3 |
| accepted, v0.2 | 1 | 2 | 3 | 0 |
| rejected, v0.1 | 0 | 7 | 3 | 3 |
| rejected, v0.2 | 1 | 4 | 8 | 0 |

By reason (rejected discoveries flagged by an intended code at error or warning severity):

| Human rejection reason (paraphrased) | Discoveries | v0.1 | v0.2 | Intended codes |
|---|---|---|---|---|
| baseline too simple (random agent) | 4 | 4 (R1) | 4 (R1) | R1 |
| effect did not replicate with more samples | 3 | 3 | 3 (R2 now an error on two) | R2, R3, A6 |
| overly simple benchmark, few samples, unvalidated judge | 1 | 1 (A2) | 1 (A2) | R3, A2 |
| the agents never use the graph they build | 1 | 0 | 0 | R5 |
| agent partly hard-coded | 1 | 0 | 0 | R4 |
| both conditions hard-coded (foregone conclusion) | 1 | 0 | 0 | R4 |
| report lacks details | 1 | 1 (A7) | 0 (A7 is now a note) | A2, A4, A7 |
| unclear motivation | 1 | 0 | 0 | none (out of scope) |

**Each error-level false flag on an accepted discovery (v0.1), and what v0.2 does with it:**

| Discovery | v0.1 flag | Finding | v0.2 |
|---|---|---|---|
| 1 (simulation confidence) | A1 error on "AUC = 0.54" | Parser limit. The AUC is computed in the code and written only into the legend of a saved ROC plot (`label=f'ROC curve (AUC = {roc_auc:.2f})'`, then `savefig`); it is in an output, one the audit cannot read. | Warning, `tier: figure_only` (regression test `test_a1_number_possibly_only_in_a_saved_figure_is_a_warning`) |
| 1 | R1 error on "than random" | Parser bug. The sentence says confidence scores "perform only slightly better than random at predicting accuracy": a negative statement with chance as the natural reference of an AUC, not a random-only baseline. | Not counted (info) (`test_r1_limiting_comparison_to_chance_is_not_flagged`) |
| 3 (two-stage game generation) | A1 error on "76%" | Parser bug. "29.8 seconds ... compared to 16.9 seconds, a 76% increase": a relative change of two printed numbers (the run printed the means at full precision). | Passes as derived (`test_a1_worded_relative_change_of_printed_numbers_is_derived`) |
| 3 | A4 error on "significantly" | Genuine. The report says "significant differences" and "significantly more time"; the code runs no test and the output prints no test statistic or p value. The humans accepted the discovery anyway. | Kept as an error |
| 5 (basic confidence simulation) | A1 error on "SD = 15.8%" | Genuine. The standard deviation of per-game accuracy is printed nowhere; recomputed from the run's `results.json` it is 16.2% (sample) or 16.0% (population), not 15.8%. The humans accepted the discovery anyway. | Kept as an error (`test_a1_unprinted_statistic_stays_an_error`) |

v0.2 adds one error on an accepted discovery: discovery 2's idea has 2 supporting and 2
refuting runs, which v0.2 calls a result that does not replicate (R2 error); under v0.1 it
was a warning. That follows the recalibration rule, not a parser fix, and it is reported
as a cost. Net: errors on accepted discoveries stay at 3 of 6, but now from different causes
(two genuine, one rerun instability), and one accepted discovery passes.

- R5 does not catch discovery 12: the graph the agents build is logged (its size and
  verification rate are saved), so it is on an output path; the human reason concerns the
  headline score, which needs a slice of the reported metric that this analysis does not
  do. R4 does not catch 11 or 18: their hard-coding is in agent and environment logic, not
  in a result literal.
- A7 fires on most CodeScientist reports: they give group means and a p value but no
  effect size. In v0.2 it is an info note and does not flag.

### Held-out v0.1, preregistered (CodeScientist full50 reruns and external ratings)

**This is the rules v0.1 result, and it stays the v0.1 result.** It is not re-scored with
v0.2; `run_all.py` recomputes it with the frozen v0.1 rules taken from git, and the numbers
below are unchanged. Preregistered in `prereg/audit/heldout_prereg.md` (commit 3d86441),
committed before any scoring, with the rules frozen at d24d2f7; the scoring script
(`analyses/audit/codescientist_heldout.py`) checks that the rules it runs are that tree. Predictor: a run is flagged when it has any error-severity check
(R2 off, since it would read the outcome).

**H1 (confirmatory, labelled heldout): not supported; the difference is in the opposite
direction.** Units: 80 judged full50 runs from ideas with at least 2 judged runs (10
development-set directories, 13 runs of ideas with a single judged run and 1 run without a
judgement excluded). Outcome: leave-one-out agreement of a run's meta-analysis judgement
with the other runs of its idea.

| | runs | mean agreement |
|---|---|---|
| passed by the audit | 42 | 0.3433 |
| flagged by the audit | 38 | 0.4408 |

Stratified (within-idea) permutation test, 10,000 draws, seed 20261117: two-sided
p = 0.0845. The prediction was that flagged runs agree less; they agreed more, and the
difference is not significant at 0.05. Secondary, no decision: Mann–Whitney p = 0.1431;
without any run of the 19 development ideas (20 runs left) p = 0.4878.

**H2 (exploratory: the 20 rated papers are the development directories, so not blind):
null.** Mean binarised external soundness 0.6667 for the 11 papers the audit passes and
0.6296 for the 9 it flags; permutation p = 0.8561, Mann–Whitney p = 0.8061.

Reading: on these data the audit's error flags do not predict which CodeScientist runs
replicate in their reruns or which papers external reviewers rated sound. The flags mark
specific, checkable defects (an unprinted number, a missing test, a random-only
comparator); the outcomes here are model-judged rerun agreement and three human ratings
per paper, and neither moves with those defects at this sample size.

### Held-out v0.2, preregistered (the 13 unused full50 runs): not testable

**Which data H1 used.** The `codescientist-full50` archive holds only the with-expert-notes
batch (104 run directories); the without-expert-notes batch has meta-analysis files and a
bulk TSV in the repository but no released run directories, so it cannot be audited. H1
scored 80 of the 104 directories; 10 are development-set directories (11 counting a
follow-on run without a judgement); the remaining **13 runs** (ideas with a single judged
run) were never audited by any version and were in neither H1 nor H2. They are the only
unused, auditable data, and the v0.2 held-out test uses them.

Preregistered in `prereg/audit/heldout_v2_prereg.md` (commit 75b85b4), committed after the
v0.2 rules were frozen (commit fd0187a, tree `5aa8b9c` of `consilience_ai2/audit`) and
before any of these runs was audited; `analyses/audit/codescientist_heldout_v2.py` checked
that tree when it scored. **H3 (confirmatory):** runs the v0.2 audit flags at error
severity are less often rated faithful to their plan (`faithfullness_category` in the
with-expert-notes bulk TSV: faithful 1, deviations or errors 0) than runs it passes.
Outcome chosen in advance because leave-one-out agreement is undefined for single-run
ideas and the support/refute judgement does not measure soundness. Test: two-sided
permutation test of the difference in shares, 10,000 draws, seed 20261118, alpha 0.05;
not testable if either group has fewer than 3 runs.

**Result (labelled heldout): not testable.** The v0.2 audit put an error on 1 of the 13
runs (an R1 random-only comparator) and passed 12 (3 with no error or warning, 9 with
warnings only, mostly A6 underpowered nulls). One flagged run is below the preregistered
minimum of 3 per group, so no test was run and H3 is neither supported nor refuted. This is
a limit of the data, not a null result: the only fresh runs are too few and too rarely
flagged. The frozen v0.1 rules also flag just 1 of the 13 (exploratory secondary (d)), and
without the 2 runs of development ideas the split is 1 of 11 (secondary (b)); neither is
testable either.

**Exploratory, not blind for the runs (secondary (c)).** The same predictor and outcome on
the 79 H1 units that have a faithfulness category (runs already used in the v0.1 held-out
test; this outcome was never looked at before): 50% of the 42 passed runs and 37.84% of
the 37 flagged runs were rated faithful, a difference in the predicted direction that is
not significant (permutation p = 0.3663; Fisher p = 0.3647).

### A5 on DiscoveryBench synthetic tasks (labelled descriptive; null control synthetic)

`analyses/audit/discoverybench_a5.py`. **Machine-readable set.** Of the 903 synthetic
queries, 157 were scanned with their machine-readable gold relation (`target_col`,
`relevant_cols`): 720 have none (only a natural-language question or hypothesis; see the
derived set below) and 26 have a constant target. For each scanned task
every column is tested against the target (Spearman for numeric pairs, point-biserial for
binary-numeric, Kruskal–Wallis for categorical-numeric, chi-square for categorical pairs;
two-sided; pairwise-complete rows), then BH within the task.

| | raw p < 0.05 | BH q < 0.05 |
|---|---|---|
| distractor columns with a hit (n = 4456 tests) | 7.4% (331) | 2.7% (122) |
| tasks with at least one distractor hit (n = 157) | 75.2% | 38.9% |
| gold columns detected (recall, n = 575) | 57.9% | 52.35% |
| permuted-target control: hits (n = 5031 tests) | 4.7% | 0.1% |
| permuted-target control: tasks with any hit | 73.25% | 3.8% |

BH removes 63.1% of the distractor hits. Caveat: the synthetic generator builds columns from a semantic tree, so a distractor can
be genuinely associated with the target and a distractor hit is "outside the gold
relation", not necessarily false. The permuted-target control (target shuffled with
`numpy.random.default_rng(20261117 + task index)`) is where every hit is false by
construction: raw testing gives at least one false discovery in most tasks, BH in few.
Gold recall is limited because gold columns enter the target through nonlinear and
conditional formulas that a marginal test can miss.

**Derived set (rules v0.2, labelled separately).** The 720 queries without a
machine-readable relation get a target and gold columns from a fixed, documented rule
(`consilience_ai2.audit.discoverybench.derive_gold`): text and column names are
lower-cased with every run of non-alphanumerics made one space (`conflict_ratio` becomes
"conflict ratio"); a column is mentioned when its name occurs in the question or gold
hypothesis as whole words (a shorter name inside a mention of a longer one does not
count); the derived target is the column named first in the question (else in the
hypothesis), the derived gold columns are the other mentioned columns. 534 of the 720
queries name a target and at least one gold column; 51 of those have a constant target,
so 483 were scanned. The rule was fixed before it was run, not tuned.

Agreement, where both exist (the rule applied to the 183 machine-readable queries; 153 of
them give a usable derivation): the derived target equals `target_col` in 32.68% of them;
of the derived relation columns (target and gold) 95.96% are in the machine-readable
relation (pooled, n = 520), and they cover 68.45% of it (n = 729). The rule finds real
relation columns but often picks the wrong one as the target, so a "distractor" in the
derived set can be the true target's parent, and its distractor and gold numbers are less
clean than the machine-readable set's.

| derived set | raw p < 0.05 | BH q < 0.05 |
|---|---|---|
| distractor columns with a hit (n = 15356 tests) | 7.42% (1139) | 2.79% (428) |
| tasks with at least one distractor hit (n = 483) | 85.3% | 42.24% |
| derived gold columns detected (n = 1010) | 35.15% | 30.3% |
| permuted-target control: hits (n = 16366 tests) | 5.17% | 0.23% |
| permuted-target control: tasks with any hit | 79.5% | 6.63% |

BH removes 62.42% of the distractor hits in the derived set. **Coverage:** 17.39% of the
903 queries with the machine-readable relation alone; 70.87% with the machine-readable or
the derived relation.

### Reproducing a published number

The CodeScientist resistor report's success-rate table (Table 4, discovery 4) reproduces
exactly from its `results.json`: 9 of 9 cells, each 100 times the mean of the matching
`within_k_percent` boolean per method, agree at the printed precision
(`tests/audit/test_audit_tables_and_resistor.py`).

### Real AutoDiscovery outputs: searched, none public

The AutoDiscovery adapter has only been run on synthetic fixtures. A search for any public
output of a real AutoDiscovery run (node files, `mcts_nodes_all.json`, a hosted
`results.json`, a `validity_audit`-like export) on 18 November 2026 found none:

| Where | What was there |
|---|---|
| `allenai/asta-autodiscovery` at 30e080f (also the remote HEAD on that date; tests, examples, docs, UI) | Code and unit tests with monkeypatched runs; `ui/e2e-report/make_report.py` writes an invented "synthetic soil study" run for the report viewer's smoke test |
| `allenai/asta-plugins` at a2dcade and the remote HEAD f980bb7, every branch's history | The autodiscovery-exploration workflow's `experiments.csv` and `runs.csv` templates (header rows only), JSON schemas, `tests/test_autodiscovery_results.py` (a fake client) |
| Hugging Face API: datasets by `allenai` searched for autodiscovery, autods, auto-discovery, discovery, surprisal, mcts; all datasets for autodiscovery and autods; `allenai` models and spaces for autodiscovery | Only `allenai/discoverybench` (benchmark tasks, not runs); two unrelated third-party datasets named auto_ds or autods |
| GitHub `allenai/*` by name (`git ls-remote`; the org API is not reachable from here) | `allenai/autodiscovery` (the NeurIPS 2025 code, 66aa2d5; `autods` and `AutoDS` resolve to it): code, two logos, no outputs in any commit. `allenai/asta-bench`: no AutoDiscovery files. Names such as autodiscovery-results, autodiscovery-data and autods-data do not exist |
| The AutoDiscovery paper (arXiv 2507.00310v3) | No ancillary files. The source's appendix quotes four code-execution outputs (a random forest, two regressions, a clustering) without the code, analysis, hypothesis or beliefs of their nodes, so there is no node to audit. The 175 annotated `nls_bmi` nodes of its validity study are not released. OpenReview's API refused automated access |

So the adapter's transfer to real runs remains untested; no fetch source was added.

## Limits

- **Small n.** The dev set is 19 discoveries; the v0.1 held-out tests have 80 runs (from 24
  ideas at most) and 20 papers. Differences of the size these data allow are noisy.
- **No fresh held-out test of v0.2 was possible.** The only unused auditable data are 13
  full50 runs; v0.2 flags 1 of them at error severity, below the preregistered minimum
  group size, so H3 is not testable. Every other public CodeScientist run with released
  files has been used in development or in the v0.1 held-out test. The v0.2 numbers above
  are dev (not blind) or exploratory.
- **The v0.1 held-out prediction failed.** Error-level flags did not predict lower rerun
  agreement or lower external soundness, and v0.2 has no held-out result of its own; the audit's value has to rest on the defects it
  names (each with a receipt), not on predicting replication.
- **The dev set is not blind.** The v0.1 rules were written knowing the CodeScientist
  rejection reasons, the v0.2 recalibration was decided after inspecting the same cases,
  and the external-ratings test uses the same 20 papers, so it is exploratory.
- **Rule versions.** v0.1 and v0.2 results are reported side by side and never mixed: the
  v0.1 held-out result stays the v0.1 result (recomputed from the frozen v0.1 rules), and a
  v0.2 held-out claim needs its own preregistered test.
- **A1 tiers are lexical.** A "derived" number is a ratio, relative change or difference of
  two printed numbers of its sentence near change wording; a coincidence can pass. A
  "figure-only" warning means the code writes formatted values into saved figures, not that
  this number is in one. The coarser-precision warning needs a printed number with at least
  3 significant digits; a less specific one is not taken as support.
- **R2 depends on how reruns are matched.** The CodeScientist labels are of an idea's five
  original runs; a follow-on experiment is judged by them.
- **The derived DiscoveryBench gold is approximate.** The rule picks the right target in
  about a third of the machine-readable queries; its numbers are reported apart from the
  machine-readable set.
- **No real AutoDiscovery run is public** (search above). The AutoDiscovery adapter is
  tested only on schema-faithful synthetic fixtures; transfer of the rules to real
  AutoDiscovery runs is unproven.
- **Regex-level parsing is brittle.** n, p values, test statistics, effect sizes, claim and
  comparator words are read with fixed patterns. They catch wording, not intent: a report
  can be flagged for a number it computed correctly but did not print (A1), and a defect
  phrased unusually is missed.
- **R5 is scoped.** It finds components that reach no output at all, not components that
  miss the headline metric; it assumes the listed methods do not mutate their receiver.
- **A5 depends on parse coverage.** Runs that print no p values get no q; coverage is
  reported per run and must be read with the q values.
- **A6 and R3 treat the largest parsed n as the per-group n,** which is generous to the
  experiment; real designs with several arms have less power than these bounds suggest.
- **CodeScientist rerun and consistency labels are model-generated** (released data, not
  produced here); R2 inherits their errors.
