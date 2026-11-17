---
name: experiment-audit
description: Run a deterministic, receipt-backed audit over an agent-run experiment and read its verdicts — an AutoDiscovery output directory (mcts_node_*.json, mcts_nodes_all.json, a hosted results.json) or a CodeScientist experiment directory. Checks that reported numbers appear in the printed output (A1), that the stated n matches (A2), that columns exist in the dataset metadata (A3), that "significant"/"surprising" has a printed test (A4), Benjamini–Hochberg q across the run (A5), the minimum detectable effect of a surprising null (A6), an effect size (A7), random-only baselines (R1), rerun flips (R2), a power-based n floor (R3), hard-coded result literals (R4) and built-but-unused components (R5). Triggers on "audit this run", "check the AutoDiscovery results", "are these experiments valid", "validity audit", "multiple testing across the run", or a request to double-check AutoDiscovery's Validity Check.
allowed-tools: Read Grep Glob Bash(consilience-ai2 audit *) Bash(python -m consilience_ai2 audit *) Bash(pip install *consilience-ai2*) Bash(uv tool *)
---

# Experiment audit

A deterministic second signal beside AutoDiscovery's language-model "Validity Check". It never calls a model and never judges the reviewer's text: that text is hashed and kept next to each verdict. The same input gives byte-identical output.

## Procedure

1. **Find the run.** A local AutoDiscovery run is its `--out_dir` (it holds `mcts_node_*.json` and `args.json`). A hosted run is the file written by `asta autodiscovery results <run_id> -o results.json`. A CodeScientist experiment is a directory with `history.json` and `modal-python-*/`.
2. **Find the dataset metadata** (AutoDiscovery only): the file passed as `--dataset_metadata`. Without it, A3 (columns not in the data) is not checked; say so.
3. **Run the audit.**

   ```bash
   consilience-ai2 audit run <out_dir> --metadata <dataset_metadata.json>
   ```

   It writes `<out_dir>/validity_audit.json` (or `--json OUT`), prints one line per experiment (`<id>: pass|flag|refuse q=<q> <codes>`), then GitHub annotation lines for every error and warning. Exit 1 means at least one error-severity finding.
4. **Read the verdicts, not the pass count.** `refuse` means the numbers or columns cannot be trusted (A1 an unsupported number, A3 a column not in the data) or nothing could be checked (U1). `flag` lists codes to read. `pass` means no rule fired — not that the finding is true.
5. **Quote receipts.** Every finding names the file, the field (`mcts_node_2_1.json#analysis`), the line or character offsets, and the file's SHA-256. When you report a problem, cite that receipt and the span as written.
6. **Keep the two signals separate.** Report the audit's verdict beside the Validity Check's pass flag (`llm_validity_check.success`); do not overwrite either, and do not re-judge the reviewer's text.

## What it does not do

It reads wording and numbers, not intent. It cannot tell whether a method suits the data, whether a finding makes domain sense, or whether a hypothesis is interesting. R5 catches only components whose output reaches no printed or saved result at all. Regex-level n parsing is brittle; check A2 findings by hand. The rules were developed on CodeScientist data, and no real AutoDiscovery run is public, so transfer to AutoDiscovery runs is unproven.
