# Limitations

What the three tools cannot do, and how far the reported results can be trusted. Each
component's own document has the full detail: [receipts](receipts.md),
[audit](audit.md), [reproduce](reproduce.md). Every number below renders from
`results/registry.json`; see [RESULTS.md](RESULTS.md) for n and intervals.

## What the results rest on

- **No real AutoDiscovery run is public.** The AutoDiscovery adapter of the audit is
  tested only on synthetic fixtures written from the released schema
  (`MCTSNode.to_dict` at asta-autodiscovery commit 30e080f). They show that the adapter
  reads the format, not that the rules transfer to real AutoDiscovery runs. The in-run
  wrapper (`examples/audit/run_with_audit.py`) was exercised only against those
  fixtures; no AutoDiscovery run was made.
- **The audit's development set is not blind.** The rules were written knowing the
  CodeScientist reviewers' rejection reasons for the 19 discoveries of the paper's
  Table 4. The dev numbers measure fit to the cases that motivated the rules, not
  generalisation. The external-ratings test (H2) uses the same 20 papers, so it is
  labelled exploratory, not held-out.
- **The audit's held-out prediction failed.** Preregistered H1 predicted that runs the
  audit flags agree less with their reruns. They agreed more (0.4408 against 0.3433),
  and the difference is not significant (stratified permutation p = 0.0845). H2 is null.
  The audit's value has to rest on the specific, receipt-backed defects it names, not on
  predicting replication.
- **The receipts held-out test is a null.** On SciArena, the response with the higher
  W1+W2 flag rate lost the human vote in 50.09% of 569 included votes (sign-test
  p = 1.0). This is no evidence of a difference at that sample size; it is not evidence
  that there is none.
- **Small n.** The audit's dev set is 19 discoveries; its held-out tests have 80 runs
  (from at most 24 ideas) and 20 papers. Several exploratory splits (Theorizer by
  predictive accuracy, SciArena W1 or W2 alone) have groups of a few hundred or fewer.
  Effects of the size these data can show are noisy.
- **Low coverage on CodeScientist reruns.** Read as reproductions, only 36.92% of the 65
  (source, rerun) pairs (95% CI 26.23% to 49.08%) have the numbers the verdict needs in
  both runs' results files. The rest are classed `no_data`, so most verdicts there are
  `inconclusive` by construction. The reruns are reruns in the same environment, not
  independent data, and the thresholds were fixed by this analysis, not by the runs'
  authors.
- **Labels from other systems are not ground truth.** CodeScientist's per-run
  support/refute/inconclusive judgements and its consistency labels are language-model
  readings of each run's write-up (released data, not produced here). The audit's R2 and
  both components' agreement figures inherit their errors.
- **DiscoveryBench label impurities.** "Planted" means a column appears in a task's gold
  expression, not that its effect is linearly detectable; "null" means no query names
  the column, not that it is independent of the target. The generator builds columns
  from a semantic tree, so a "null" can be genuinely associated with the target (all 35
  reproduced nulls are significant on the whole table), and a distractor hit in the A5
  scan is "outside the gold relation", not necessarily false. Only the permuted-target
  control is false by construction. 720 of the 903 synthetic queries have no
  machine-readable gold relation and are not used by the A5 scan.
- **Synthetic suites are true by construction.** The seeded workspace (100% recall of
  17 planted defects, 0 false findings on the controls) and the synthetic AutoDiscovery
  run show that the rules do what they say. They do not say how often real outputs have
  these defects.

## What the checks can and cannot see

- **Lexical, not semantic (receipts W1, W2).** W1 compares numbers and W2 compares words
  from a fixed, published list. Neither judges meaning or support. A W1 number may come
  from elsewhere in the paper, a calculation or a unit conversion; a W2 word may be
  appropriate in context; the lists miss hedges and assertions phrased in other words;
  negation is read only within two words. Whether a quote supports a claim is out of
  scope (asta-plugins leaves that to its `check-claims` skill).
- **E6 needs local text.** Without `--sources`, every quote is `UNCHECKABLE`. Quotes are
  compared as written in `evidence.yml` (Markdown in a quote is not rendered), and text
  extracted from a PDF can differ from the published wording in ways the normalisation
  does not cover (reflowed tables, dropped symbols).
- **Regex-level parsing.** The audit reads n, p values, test statistics, effect sizes and
  claim and comparator words with fixed patterns; the receipts checker reads workspaces
  with a reimplementation of what Quarto and the evidence filter read. They catch
  wording, not intent. A report can be flagged for a number it computed correctly but
  did not print (A1), and a defect phrased unusually is missed. Not read: directory-level
  `_metadata.yml`, Quarto profiles, includes, YAML merge keys, and attribute values that
  contain backticks.
- **Numbers.** Numbers written as words, year-like integers (1900 to 2100) and ambiguous
  separators (`1,2`, `1.234,5`) are not checked; ambiguous ones are reported as
  uncheckable, never as a mismatch. Absolute values are compared, so a sign error is not
  flagged. `10^2` is read as two numbers.
- **R5 is scoped.** It finds components whose results reach no printed or saved output
  at all, not components that miss the headline metric; code using `eval`, `exec`,
  `globals`, `setattr` or a computed `getattr` is reported as not decidable.
- **A5 depends on parse coverage.** A run that prints no p values gets no q; coverage is
  reported per run and must be read with the q values. A6 and R3 treat the largest
  parsed n as the per-group n, which is generous to the experiment.
- **Reproduction records are declarations.** F1 checks a declared same quantity, proxy
  or substitution against names, units, effect types and conditions; it cannot tell a
  well-named substitution from a reproduction. Power is closed-form for four effect
  types (`r`, `d`, `dz`, proportions) and anything else is `uncheckable`, not
  approximated. Power is computed at the source effect, itself an estimate that is often
  inflated when the source was selected for being surprising.
- **P1 trusts git.** Commit order is read from the commit graph, not wall-clock truth;
  rewritten history can fake it. The shipped example records were committed with their
  thresholds and results in one commit, so P1 reports them as
  `thresholds_post_hoc(same_commit)`, correctly.
- **P2 is strict.** Any rewording of the hypothesis is an error by design; a faithful
  paraphrase is not distinguished from a distortion.
- **Snapshots of other projects.** The E5 list of `asta` subcommands is read from
  asta-plugins at commit a2dcade; the reproduction rubric from the asta-flows workflow
  at the same commit; the AutoDiscovery schema at commit 30e080f. New upstream versions
  need new rule versions.

## Determinism

The same input gives byte-identical output for each tool. The analyses are
byte-identical across reruns on the same data with the same numpy and scipy versions;
some exact confidence bounds kept unrounded in `analyses/receipts/examples.json` can
differ in the last floating-point digit across scipy versions. The values in the
results files are rounded and were checked identical across reruns.
