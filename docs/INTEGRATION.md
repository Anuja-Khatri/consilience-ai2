# Integration

Where each tool hooks into the Asta tools, as file formats and commands. Nothing here
patches Ai2's code: every hook is a command run beside it, a Makefile snippet the
project includes, or a script the project copies in. Hook points were read from
asta-plugins at commit a2dcade and asta-autodiscovery at commit 30e080f.

Install the command once wherever the hook runs:

```bash
pip install "git+https://github.com/Anuja-Khatri/consilience-ai2"
# with unit-aware comparability for reproduce (optional)
pip install "consilience-ai2[consilience] @ git+https://github.com/Anuja-Khatri/consilience-ai2"
```

All three tools share one exit-code contract: `0` no error-severity finding, `1` an
error-severity finding or an input that cannot be read, `2` a usage error. Each prints
GitHub annotation lines (`::error file=…,line=…::CODE message`), so a CI step shows
findings inline on the pull request.

## 1. Evidence receipts in a workspace's `make check`

**Reads** an asta-plugins workspace as it is: the evidence store (`metadata-files` in
`_quarto.yml`, else `evidence.yml`), the bibliography (`bibliography`, else
`references.bib`), and every `*.qmd` with `[…]{.ev key="…"}` spans and inline `quote=`.
`--sources` adds local source text for the verbatim check (E6): a directory of
`<cite>.txt` / `<corpus_id>.txt`, a Theorizer PaperStore JSON, or an AutoDiscovery
exploration `index.json`.

**Hook.** The workspace Makefile runs its gates under `check`, and a project may add
its own gates as prerequisites ("when a project grows a new gate, add it here (or as a
prerequisite target)"). The plugin ships a snippet that does exactly that:
`plugins/consilience-receipts/skills/evidence-receipts/assets/evidence-receipts.mk`.

```bash
cp plugins/consilience-receipts/skills/evidence-receipts/assets/evidence-receipts.mk <workspace>/
echo 'include evidence-receipts.mk' >> <workspace>/Makefile   # or the project-owned workspace.mk
make -C <workspace> check
```

`make check` then also runs

```bash
consilience-ai2 receipts check . --json _receipts/receipts.json
```

and fails on any E code. Settings (set before the include or on the command line):
`CONSILIENCE_AI2` (the command), `RECEIPTS_DIR` (default `.`), `RECEIPTS_SOURCES`
(passed as `--sources`), `RECEIPTS_REPORT` (default `_receipts/receipts.json`) and
`RECEIPTS_FLAGS` (for example `--fail-on-warnings` to fail on W1/W2 too).
`tests/receipts/test_plugin.py` runs this target against the synthetic workspaces.

**Writes** the report below, plus annotation lines in the style of the workspace's
`quarto-check.sh`.

## 2. Experiment audit after an AutoDiscovery run

**Reads** an AutoDiscovery `--out_dir` (`mcts_node_<level>_<idx>.json`, else
`mcts_nodes_all.json`, else `mcts_nodes.json`, plus `args.json`), or a hosted run's
`results.json` from `asta autodiscovery results <run_id> -o results.json`. The dataset
metadata (the file given to `--dataset_metadata`) is read from `args.json` when it
resolves, or from `--metadata`; without it A3 is not checked. It also reads a
CodeScientist experiment directory (`history.json`, `modal-python-<ts>/`,
`report/report.tex`), or a directory of them.

**Hook: a post-run command.** No change to AutoDiscovery:

```bash
auto-discovery … --out_dir runs/r1 --dataset_metadata data/metadata.json
consilience-ai2 audit run runs/r1 --metadata data/metadata.json
# writes runs/r1/validity_audit.json; exit 1 when any node has an error-severity finding
```

It prints one line per node (`<id>: pass|flag|refuse q=<q> <codes>`), then annotation
lines. AutoDiscovery's own "Validity Check" (the node's `review` and `success`) is not
judged: its text is hashed and stored beside each verdict as `llm_validity_check`.

**Optional: an in-run wrapper (example only).** `examples/audit/run_with_audit.py`
wraps `autodiscovery.mcts_utils.save_nodes` from outside, in the pattern of
asta-plugins' `run_relaxed.py`, and adds a `deterministic_checks` field to each node
dict before AutoDiscovery saves it. `MCTSNode.init_from_dict` ignores unknown keys, so
the saved files still load. It must run on AutoDiscovery's own Python with
consilience-ai2 installed there:

```bash
"$(uv tool dir)/asta-autodiscovery/bin/python" -I examples/audit/run_with_audit.py <auto-discovery args>
```

It stops if `save_nodes` is not found. It was exercised only against the synthetic
fixtures in `examples/audit/autodiscovery/`; the post-run command is the supported hook.

**Plugin skill:** `consilience-audit` / `experiment-audit` runs the same command.

## 3. Reproduction verdicts beside the secondary-reproduction workflow

**Reads** a reproduction record, YAML or JSON, version 1, defined by
`consilience_ai2/reproduce/data/reproduction_record.schema.json`: the hypothesis and the
source run's hypothesis; the source and reproduction measurements (quantity, value,
unit, n, effect size, p, interval, conditions); the declared quantity mapping
(`same_quantity`, `proxy`, `substitution`); the independence axis; the thresholds with
the commit that fixed them; and the commit of the result. Worked synthetic records are
in `examples/reproduce/records/`.

**Hook: a `verdict.py` drop-in.** The asta-flows "Secondary reproduction" workflow keeps
helper scripts in a run's `scripts/` (as the exploration workflow does with `check.py`
and `runlog.py`). Copy `examples/reproduce/verdict.py` there:

```bash
cp examples/reproduce/verdict.py <run>/scripts/verdict.py
python <run>/scripts/verdict.py                 # every <run>/reproduction/*.yaml
```

It writes `reproduction/reproduction_verdict.json` (every record's report) and
`reproduction/mission_verdicts.txt`, the REPRODUCED / NOT REPRODUCED / UNDECIDED block of
the workflow's `mission.md`, filled from the numbers. Commit each record's thresholds
before its result: P1 reads the git history. For one record:

```bash
consilience-ai2 reproduce check reproduction/H1.yaml --json reproduction/H1.verdict.json
```

**Plugin skill:** `consilience-reproduce` / `reproduction-verdict`.

## 4. Output schemas (version 1)

Every report is one JSON object, written with sorted keys and no timestamp, so the
same input gives the same bytes. The shared fields come from `consilience_ai2.core.findings`:

| Field | Meaning |
|---|---|
| `version` | `1` |
| `tool`, `tool_version` | for example `"consilience-ai2 receipts"`, `"0.1.0"` |
| `inputs` | each input read: `path` (relative), `role`, `sha256` |
| `findings` | each with `code`, `severity` (`error`, `warning`, `info`), `message`, `file`, `line`, `key`, `receipt`, `details` |
| `receipt` | `source` (what was checked, e.g. `file:smith2024.txt`, `evidence:<key>`, `record:<file>#<field>`), `sha256` of that source, `offset` and `end` (character span, or null), `normalisation` (the text-normalisation version, or null) |
| `summary` | `total`, `by_severity`, `by_code` |

Passing checks are findings too, with severity `info` and a receipt. Component fields
sit beside these. The examples below are abbreviated from the shipped examples (`…`
marks elided values).

### receipts: the report

Extra fields: `checked_spans`, `entries`, `sources` (kind and size of the local text),
`rules` (the normalisation, certainty-word and asta-method list versions).

```json
{"version": 1, "tool": "consilience-ai2 receipts", "tool_version": "0.1.0",
 "checked_spans": 26, "entries": 20,
 "rules": {"asta_methods": "consilience-ai2.asta-methods/1",
           "certainty_words": "consilience-ai2.certainty/1",
           "normalisation": "consilience-ai2.normalise/1"},
 "sources": {"files": 3, "kind": "directory"},
 "inputs": [{"path": "evidence.yml", "role": "evidence", "sha256": "…"}, …],
 "findings": [
   {"code": "E6", "severity": "info", "file": "controls.qmd", "line": 8, "key": "c-ligature",
    "message": "FOUND in file:smith2024.txt at [231, 280)",
    "details": {"occurrences": 1, "outcome": "FOUND"},
    "receipt": {"source": "file:smith2024.txt", "sha256": "4405fe97…", "offset": 231,
                "end": 280, "normalisation": "consilience-ai2.normalise/1"}},
   {"code": "W1", "severity": "warning", "file": "defects.qmd", "line": 25,
    "key": "d-number-overreach",
    "message": "number in the claim not in the quote: …",
    "details": {"claim": "…", "unsupported": ["…"], "unsupported_offsets": [[15, 20]],
                "supported": [], "ambiguous": [], "years_skipped": []},
    "receipt": {"source": "evidence:d-number-overreach", "sha256": "…", "offset": null,
                "end": null, "normalisation": null}}],
 "summary": {"total": 39, "by_severity": {"error": 14, "warning": 3, "info": 22},
             "by_code": {"E1": 2, "E2": 3, "E3": 2, "E4": 1, "E5": 5, "E6": 23, "W1": 2, "W2": 1}}}
```

E6 `details.outcome` is `FOUND`, `NOT_FOUND` or `UNCHECKABLE`.

### audit: `validity_audit.json`

The shared fields, plus the per-node layout of the spec: `run`, `format`
(`autodiscovery` or `codescientist`), `n_nodes`, `n_with_pvalue`, `parse_coverage`
(`nodes_checkable`, `nodes_with_pvalue`, `pvalues`, `rate`), `verdicts` (counts),
`rules_version`, `rules` (each code's rule text and status), `notes`, and `nodes`. Each
node has its `verdict` (`pass`, `flag`, `refuse`), `codes`, `q_value` (the smallest
Benjamini–Hochberg q among its p values, or null), `not_applicable`,
`llm_validity_check` (AutoDiscovery's pass flag and the SHA-256 of its review text), and
`checks`, each with the field and span as written and the receipt flattened in.

```json
{"version": 1, "tool": "consilience-ai2 audit", "tool_version": "0.1.0",
 "run": "synthetic_run", "format": "autodiscovery", "n_nodes": 12, "n_with_pvalue": 10,
 "parse_coverage": {"nodes_checkable": 11, "nodes_with_pvalue": 10, "pvalues": 15, "rate": "…"},
 "verdicts": {"flag": 8, "pass": 1, "refuse": 3}, "rules_version": "audit-rules-1",
 "nodes": [
   {"id": "node_2_1", "verdict": "refuse", "codes": ["A1"], "q_value": "…",
    "surprising": true, "not_applicable": ["A6", "R1", "R2", "R4"],
    "llm_validity_check": {"success": true, "text_sha256": "c3398653…"},
    "checks": [
      {"code": "A1", "severity": "error", "field": "analysis", "span": "…",
       "message": "… is not printed in the run's output or code at the printed precision",
       "file": "mcts_node_2_1.json", "line": 1, "offset": 32, "end": 36,
       "source": "mcts_node_2_1.json#analysis", "sha256": "37a64e60…",
       "details": {"checked": 2, "value": "…"}}, …]}, …],
 "findings": […], "inputs": […], "summary": {…}}
```

The in-run wrapper stores a node's verdict, codes, q value, `llm_validity_check` and its
non-info checks under `deterministic_checks` in the node dict, with `tool`,
`tool_version` and `rules_version`.

### reproduce: `reproduction_verdict.json`

Extra fields: `record` (`path`, `sha256`, `id`), `rubric` (the asta-flows source),
`checks_skipped`, and `verdict`:

```json
{"version": 1, "tool": "consilience-ai2 reproduce", "tool_version": "0.1.0",
 "record": {"id": "H1-sleep-recall", "path": "supported.yaml", "sha256": "2c1b2c3b…"},
 "verdict": {"faithfulness": "same_quantity", "decidability": "decidable",
             "outcome": "supported", "outcome_label": "supported", "reason": null,
             "verdict": "reproduced", "commit_order": "thresholds_post_hoc(same_commit)",
             "hypothesis_copy": "verbatim", "caveats": []},
 "findings": [
   {"code": "D1", "severity": "info", "file": "supported.yaml", "line": 16,
    "key": "H1-sleep-recall", "message": "decidability: decidable",
    "details": {"decidability": "decidable", "effect_type": "r", "n": 180,
                "power": "…", "power_threshold": 0.8, "alpha": 0.05, "sides": 2, …},
    "receipt": {"source": "record:supported.yaml#reproduction", "sha256": "2c1b2c3b…",
                "offset": null, "end": null, "normalisation": null}}, …],
 "summary": {"total": 5, "by_severity": {"error": 1, "warning": 0, "info": 4},
             "by_code": {"D1": 1, "F1": 1, "P1": 1, "P2": 1, "V1": 1}}}
```

`verdict.verdict` is `reproduced`, `not_reproduced` or `inconclusive`; `outcome_label`
gives the rubric outcome (`supported`, `opposite_effect`, `rejected`,
`undecided(<reason>)`, `not_a_reproduction`). The `verdict.py` drop-in wraps one report
per record as `{"version": 1, "records": [ … ]}`.

## 5. Claude Code plugins

The repository is a Claude Code plugin marketplace in the asta-plugins layout
(`.claude-plugin/marketplace.json`, `plugins/<plugin>/skills/<skill>/SKILL.md`, no
per-plugin `plugin.json`):

```bash
claude plugin marketplace add Anuja-Khatri/consilience-ai2
claude plugin install consilience-receipts@consilience-ai2
claude plugin install consilience-audit@consilience-ai2
claude plugin install consilience-reproduce@consilience-ai2
```

| Plugin | Skill | Runs |
|---|---|---|
| `consilience-receipts` | `evidence-receipts` | `consilience-ai2 receipts check`; ships the `make check` snippet |
| `consilience-audit` | `experiment-audit` | `consilience-ai2 audit run` |
| `consilience-reproduce` | `reproduction-verdict` | `consilience-ai2 reproduce check` |

The skills call the `consilience-ai2` command, which must be installed (above).
