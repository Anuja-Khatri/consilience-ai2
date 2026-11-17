# C2 Experiment audit (`consilience-ai2 audit`)

A deterministic, receipt-backed audit of agent-run experiments. It reads AutoDiscovery
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
per node (`<id>: pass|flag|refuse q=<q> <codes>`) and GitHub annotation lines for errors
and warnings. Exit 0 when no node has an error-severity finding, 1 otherwise or on
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

## Checks

Severities are fixed. A node's verdict is **refuse** on U1, A1 or A3 errors (the run's
numbers or columns cannot be trusted, or nothing can be checked), **flag** on any other
error or warning, **pass** otherwise. "Pass" means no rule fired, not that a finding is
true. A check that cannot apply to a node is listed in `not_applicable`.

| Code | Severity | Rule (exact) |
|---|---|---|
| U1 | error | Uncheckable: the node has no evidence text, or no claim text. |
| A1 | error | Every decimal or percentage in a claim field appears in the evidence (any number printed anywhere in the output or results files), in a code literal, or in the plan, at the printed precision (`core.numbers.agrees_at_printed_precision`; half-up or half-even; absolute values; also x100 and /100, so a printed percentage matches a printed fraction). Integers are not checked here (A2 covers sample sizes). Bounds (`<`, `>`, "less than", "at least", "over"...) and ambiguous separators are skipped and counted. |
| A2 | warning | A stated n (`n = 50`, `N: 50`, or `<k> <unit>` with k of at least 5 from a fixed unit list: episodes, games, samples, participants, ...) in a claim or the plan must be printed (the same patterns in the output, sample-size keys in `results.json`, or a list length) or be an integer n constant in the code (a name like `N_EPISODES`, `num_samples`, a `{"PILOT": 25}` entry, a `range(N)` bound). Bounded mentions ("over 600") and mentions next to "bootstrap", "resample", "permutation", "iteration" or "steps" are skipped. |
| A3 | error (code) / warning (hypothesis) | A column the code reads from a data frame (`df["x"]`, `df[["a","b"]]`, `df.loc[:, "x"]`, `groupby("x")`, `dropna(subset=...)`, formula strings `"y ~ x"`), or a backticked or snake_case name in the hypothesis, is not a dataset column (exact or case-insensitive). Columns the code creates (assigned, `assign`, `rename`, named aggregations, `get_dummies` prefixes) are excluded. Frames are tracked through `read_*`, `DataFrame(...)`, row and column selections and frame-preserving methods; a `groupby` result is not a frame. Needs the dataset metadata. |
| A4 | error | "significant(ly)" or "surprising" in a claim, or a node marked surprising, with no test statistic or p value printed in the evidence (fixed patterns: `p = `, `t(df) =`, `chi-square`, `F(a, b) =`, `U =`, `mannwhitney`, `ttest`, `pearsonr`, `bootstrap`, a p-value key in `results.json`, ...). |
| A5 | warning | Benjamini–Hochberg across every distinct p value parsed from every node of the run (the family). Each node gets q = the smallest BH-adjusted q among its p values. A surprising node (or, without beliefs, a node claiming significance) that is not a null is flagged when q > 0.05. `p < 0.001` is kept as 0.001 (conservative); a printed 0 is kept as 0. Parse coverage (nodes with a p value / checkable nodes) is reported in `parse_coverage`. |
| A6 | warning | A surprising null is paired with its minimum detectable effect. A null is a surprising node whose posterior mean is below its prior mean with no parsed p below 0.05 (AutoDiscovery), or a null claim in the headline (a report's abstract) of a CodeScientist experiment. MDE: d = (z<sub>0.975</sub> + z<sub>0.80</sub>) · sqrt(2 / n) and r = tanh((z<sub>0.975</sub> + z<sub>0.80</sub>) / sqrt(n − 3)). Flagged when d > 0.5 (only effects larger than medium were detectable at 80% power) or n is unknown. |
| A7 | warning | A node that claims an effect (surprising, or "significant", "outperforms", "improves", "higher", "correlated", ...) reports no effect size anywhere (Cohen's d, Hedges' g, r, rho, tau, beta, odds or hazard ratio, AUC, eta squared, Cramér's V, R squared, "difference of x", or an effect-size key in `results.json`). A test statistic alone is not an effect size. |
| R1 | error | Random-only comparator: in sentences of a claim that compare (vs, versus, compared to, against, outperforms, than, over, baseline, control), a random or chance comparator is named ("random baseline/agent/policy/exploration...", "chance", "than random"), and no other comparator is: no plain "baseline"/"control" (not preceded by random, chance, additional, stronger, other...), no "X and random" coordination, no "three/four ... agents/conditions/methods". Sentences with future or modal words (should, could, future, need) are ignored. |
| R2 | warning | Rerun instability: given the verdict labels of reruns of the same idea, support and refute both occur. Needs rerun labels (CodeScientist: the meta-analysis per-run judgements); not applicable otherwise. |
| R3 | warning | A positive claim (not a null; nulls go to A6) rests on n below the floor of 25 per group: the n for 80% power to detect a large effect (d = 0.8) with a two-sided test at alpha 0.05, `ceil(2 (z_0.975 + z_0.80)^2 / d^2)`. n is the largest n printed (else stated, else a code constant), treated as the per-group n, which is generous to the experiment. |
| R4 | error | A reported decimal or percentage equals a numeric literal with at least two significant digits written in the code on the output path: an argument of a print/log/write/dump call, a constant assigned to a result-like name (accuracy, score, mean, rate, p value, ...), a result-like dict entry, or a constant returned by a result-like function. |
| R5 | error | Built-but-unused, by static analysis (Python `ast`, no execution): a top-level function or class that is used somewhere, does not itself print or save, is not the entry point, and is not in the backward slice of any output sink (print, logging calls, `write`, `json.dump`, `savefig`, `to_csv`, ...). The slice is flow-insensitive and over-approximate: attributes and subscripts collapse to their base name, branch conditions count as dependencies, an argument may be changed by any library call, and by a user function only if that function may mutate the parameter (a store into it, a method call outside a fixed non-mutating list, passing it on, or aliasing it). So a flagged component reaches no output on any path, except through dynamic features; code using `eval`, `exec`, `globals`, `setattr` or a computed `getattr` is reported as not decidable instead. **Scope:** any printed or saved output, not the headline metric. A component whose results are logged anywhere is "used" even if the reported metric ignores it. |

Rule constants: alpha 0.05 (two-sided), power 0.80, R3 effect d = 0.8, A6 bound d = 0.5, A5
threshold q = 0.05 (`consilience_ai2/audit/stats.py`).

## Output: `validity_audit.json`, version 1

A core report (`version`, `tool`, `tool_version`, `inputs` with SHA-256, `findings`,
`summary`) with the fields of needs-ledger section B.2 beside it:

```json
{"version": 1, "run": "<out_dir or run_id>", "n_nodes": 12, "n_with_pvalue": 10,
 "parse_coverage": {"nodes_with_pvalue": 10, "nodes_checkable": 11, "pvalues": 14, "rate": "..."},
 "rules_version": "audit-rules-1", "rules": {"R5": {"status": "implemented", "rule": "..."}},
 "nodes": [{"id": "node_2_1",
            "llm_validity_check": {"success": true, "text_sha256": "..."},
            "checks": [{"code": "A1", "severity": "error", "field": "analysis",
                        "span": "...", "message": "...", "file": "mcts_node_2_1.json",
                        "line": 1, "offset": 24, "end": 28, "sha256": "...",
                        "source": "mcts_node_2_1.json#analysis"}],
            "codes": ["A1"], "not_applicable": ["A6", "R2"], "q_value": "...",
            "verdict": "refuse"}]}
```

## Validation

### Synthetic AutoDiscovery fixtures (labelled synthetic)

No AutoDiscovery run outputs are public. `examples/audit/autodiscovery/` holds a
**synthetic** run written by `make_fixtures.py` from the released schema (the keys of
`MCTSNode.to_dict`, `BeliefTrueFalse.DistributionFormat.to_dict`, `ExperimentPlan` and the
hosted `ExperimentModel`, at asta-autodiscovery commit 30e080f): eleven experiment nodes,
one clean, ten each planting one defect (A1 to A7, R1, R4, R5) plus one uncheckable node,
and a hosted `results.json`. The tests assert that the audit finds exactly the planted
codes, that the fixture keys equal `MCTSNode.to_dict`'s keys read from the fetched source,
and that the fixtures regenerate byte-identically. True by construction; it shows the
adapter reads the format, not that the rules transfer to real runs.

### Development set: CodeScientist Table 4 (labelled dev)

The 19 discoveries of the CodeScientist paper's Table 4 (6 accepted, 13 rejected with the
internal reviewer's reason), matched to the 19 corresponding directories of the released
example-experiments archive. **The rules were written knowing these reasons**: this
measures fit to the cases that motivated the rules, not generalisation. R2 is given each
idea's per-run judgements from the repository's meta-analysis file. Per-discovery codes are
in `analyses/audit/dev_table.md`.

| Human rejection reason (paraphrased) | Discoveries | Caught by an intended code | Intended codes |
|---|---|---|---|
| baseline too simple (random agent) | 4 | 4 (R1) | R1 |
| effect did not replicate with more samples | 3 | 3 (R3; A6; A6 and R2) | R2, R3, A6 |
| overly simple benchmark, few samples, unvalidated judge | 1 | 1 (A2) | R3, A2 |
| the agents never use the graph they build | 1 | 0 | R5 |
| agent partly hard-coded | 1 | 0 | R4 |
| both conditions hard-coded (foregone conclusion) | 1 | 0 | R4 |
| report lacks details | 1 | 1 (A7) | A2, A4, A7 |
| unclear motivation | 1 | 0 | none (out of scope) |

- Rejected discoveries flagged by an intended code: 9 of 13 (9 of the 12 with a
  deterministic reason). Rejected with any error-severity code: 6 of 13; with any flag: 13
  of 13.
- False flags on the 6 accepted: 3 of 6 carry an error-severity code (two A1 numbers not
  printed in the output, one "significantly" with no test printed, one chance-only
  comparison read as R1), and 6 of 6 carry some flag, mostly A7 (no effect size) and R2
  (verdicts flip across reruns, which happens for accepted ideas too).
- R5 does not catch discovery 12: the graph the agents build is logged (its size and
  verification rate are saved), so it is on an output path; the human reason concerns the
  headline score, which needs a slice of the reported metric that this analysis does not
  do. R4 does not catch 11 or 18: their hard-coding is in agent and environment logic, not
  in a result literal.
- A7 fires on most CodeScientist reports: they give group means and a p value but no
  effect size. On its own it does not separate accepted from rejected work.

### Held-out, preregistered (CodeScientist full50 reruns and external ratings)

Preregistered in `prereg/audit/heldout_prereg.md` (commit 3d86441), committed before any
scoring, with the rules frozen at d24d2f7; the scoring script
(`analyses/audit/codescientist_heldout.py`) checked that `consilience_ai2/audit` was
unchanged when it ran. Predictor: a run is flagged when it has any error-severity check
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

### A5 on DiscoveryBench synthetic tasks (labelled descriptive; null control synthetic)

`analyses/audit/discoverybench_a5.py`. Of the 903 synthetic queries, 157 were scanned: 720
have no machine-readable gold relation (only a natural-language hypothesis, which this
audit does not parse into columns) and 26 have a constant target. For each scanned task
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

### Reproducing a published number

The CodeScientist resistor report's success-rate table (Table 4, discovery 4) reproduces
exactly from its `results.json`: 9 of 9 cells, each 100 times the mean of the matching
`within_k_percent` boolean per method, agree at the printed precision
(`tests/audit/test_audit_tables_and_resistor.py`).

## Limits

- **Small n.** The dev set is 19 discoveries; the held-out tests have 80 runs (from 24
  ideas at most) and 20 papers. Differences of the size these data allow are noisy.
- **The held-out prediction failed.** Error-level flags did not predict lower rerun
  agreement or lower external soundness; the audit's value has to rest on the defects it
  names (each with a receipt), not on predicting replication.
- **The dev set is not blind.** The rules were written knowing the CodeScientist rejection
  reasons, and the external-ratings test uses the same 20 papers, so it is exploratory.
- **No real AutoDiscovery run is public.** The AutoDiscovery adapter is tested only on
  schema-faithful synthetic fixtures; transfer of the rules to real AutoDiscovery runs is
  unproven.
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
