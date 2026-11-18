# consilience-ai2: technical specification

This specification defines what each tool reads, the checks it runs
(each with a stable code), what it writes, and how each tool is validated. Results are
reported in `docs/RESULTS.md` once measured; every number there renders from
`results/registry.json`.

Independent work, not affiliated with or endorsed by the Allen Institute for AI (Ai2).

## 1. Scope

The Asta tools from the Allen Institute for AI produce three kinds of scientific output:
write-ups whose claims carry evidence (the asta-plugins workspace: `evidence.yml`,
`references.bib`, `.qmd` files with `.ev` spans), experiment runs (AutoDiscovery,
CodeScientist), and reproductions of published findings (the asta-flows "secondary
reproduction" workflow). Released collaborator datasets (Theorizer, SciArena,
DiscoveryBench) have the same shapes.

consilience-ai2 is a deterministic validity layer for those outputs. It reads the files
in their native formats and runs rule-based checks. It has three tools:

- **Evidence receipts** (`consilience-ai2 receipts`): is every quote real, resolvable and
  verbatim, and does the claim overstate it in number or in certainty?
- **Experiment audit** (`consilience-ai2 audit`): do the reported numbers come from the
  run? Is the n right? Is there a real test, a real baseline, and control for many tests?
- **Reproduction verdict** (`consilience-ai2 reproduce`): is the reproduction the same
  quantity, can it be decided at all, and what do the numbers say against thresholds
  committed in advance?

It sits beside existing checks and does not replace them: where a run already has a
language-model review (AutoDiscovery's "Validity Check"), that text is hashed and kept
next to the deterministic verdict, not judged. Every finding carries a receipt (a source
hash plus a location), and every result reported for the tools is measured on data that
Ai2 and its collaborators have released.

## 2. Design principles

1. **Deterministic.** No language-model calls anywhere. The same input gives
   byte-identical output (sorted keys, no timestamps unless passed in, fixed seeds).
2. **Receipts.** Every finding names the file and line, or the character offsets, and the
   SHA-256 of the source it checked. Passing checks also emit receipts.
3. **Three outcomes, never a guess.** `pass`; `flag` (with codes); `refuse` /
   `UNCHECKABLE` when the input does not permit a decision. Unparseable input is
   reported, never skipped.
4. **Additive.** An existing review text is hashed and kept beside the verdict.
5. **Native formats, existing hooks.** Read `evidence.yml`, `.qmd` `.ev` spans,
   `mcts_node_*.json`, CodeScientist experiment directories, Theorizer exports and
   DiscoveryBench tasks as they are. Integrate at the hook points listed in section 6.
6. **No redistribution of data.** `consilience-ai2 fetch` downloads pinned sources with
   SHA-256 (files) or commit (git) checks into a cache outside the repository. The
   repository ships only small synthetic fixtures and derived numbers.
7. **Honest results.**
   - A numbers lock: every result-like number in the docs renders from
     `results/registry.json` (`scripts/numbers_lock.py`).
   - Development sets and held-out sets are labelled (`dev_or_heldout`).
   - Held-out tests are preregistered by commit before scoring (`prereg/`).
   - Limits are written down (`docs/LIMITATIONS.md`).
8. **Licensing.** The code is MIT. Third-party artefacts are credited in `NOTICE` with
   their licences: CodeScientist, asta-plugins, asta-autodiscovery and asta-theorizer
   are Apache-2.0; DiscoveryBench is ODC-BY; SciArena-Eval is MIT. Nothing gated is used.

## 3. Shared core (`consilience_ai2.core`)

| Module | Contract |
|---|---|
| `hashing` | `sha256_bytes`, `sha256_text` (UTF-8, not normalised), `sha256_file`, `canonical_json` (sorted keys, compact, NaN refused), `sha256_json` |
| `normalise` | The one text normalisation for verbatim checks, six named steps in order: ligature expansion; NFKC only for meaning-preserving compatibility forms (superscripts, subscripts and fractions kept); curly to straight quotes; removal of line-break hyphenation before a lowercase letter; removal of soft hyphens and zero-width characters; whitespace collapse. `normalise_with_map` returns an offset map from each normalised character to its original span. The rule set is versioned (`NORMALISATION_VERSION`) and the version is recorded in each receipt |
| `numbers` | Number extraction with exact `Decimal` values, printed decimal places, percent and exponent flags, `±` uncertainty links and `[start, end)` offsets. Comma and dot are read with the English convention (comma groups thousands in threes, dot is the decimal point); any other mix of separators (`1.234,5`, `1,2`, `0.1.0`) is returned as `ambiguous` and never read. `agrees_at_printed_precision` compares a value with a printed number at the printed precision |
| `findings` | `Receipt` (source id, SHA-256, offset, end, normalisation version), `Finding` (code, severity `error`/`warning`/`info`, message, file, line, key, receipt, details), `Report` (tool, version, inputs with SHA-256, findings, summary counts). Deterministic JSON; GitHub annotation lines (`::error file=…,line=…::CODE message`) |
| `registry` | CLI auto-discovery: for each of `receipts`, `audit`, `reproduce`, `fetch`, import `consilience_ai2.<name>.cli` and call `register(subparsers)`; a missing component is skipped |
| `results` | Metric records `{metric_id, value, n, ci_lo, ci_hi, source, caveats, dev_or_heldout}` written per component to `results/<component>.json`; `build_registry` merges them into `results/registry.json` |

Report format, version 1:

```json
{"version": 1, "tool": "consilience-ai2 receipts", "tool_version": "0.1.0",
 "inputs": [{"path": "evidence.yml", "sha256": "…", "role": "evidence"}],
 "findings": [{"code": "E6", "severity": "error", "message": "…", "file": "index.qmd",
               "line": 42, "key": "…",
               "receipt": {"source": "paperstore:<corpus_id>", "sha256": "…",
                           "offset": null, "end": null, "normalisation": null}}],
 "summary": {"total": 1, "by_severity": {"error": 1, "warning": 0, "info": 0},
             "by_code": {"E6": 1}}}
```

Component-specific top-level fields (for example `checked_spans`, `entries`, `nodes`)
sit beside these.

## 4. Components

### C1. Evidence receipts (`consilience-ai2 receipts`)

**Inputs**
- An Asta workspace: `evidence.yml` (`evidence: {<key>: {quote, cite?, source?, url?,
  locator?, page?, provenance?: {method, query, corpus_id, url, retrieved, note}}}`),
  `references.bib`, and `*.qmd` files with spans `[…]{.ev key="…"}` and/or inline
  `quote=`.
- Optional local source text keyed by `cite` or `provenance.corpus_id`: a PaperStore
  JSON, a directory of `.txt` files, or an AutoDiscovery `index.json`.
- Adapters for released data:
  - Theorizer exports: theories, laws with scope, evidence IDs such as `[e595.3]`, and
    the evidence extractions;
  - SciArena-Eval: responses with inline citations, each with its cited passage text.

**Checks**

| Code | Rule |
|---|---|
| E1 | Unknown `.ev` key |
| E2 | No resolvable quote |
| E3 | `cite` not in `references.bib` |
| E4 | Orphaned evidence entry (referenced by no span) |
| E5 | Provenance format: `method` an exact `asta …` subcommand, `corpus_id` an integer, `url` scheme http, https or asta, `retrieved` an ISO date |
| E6 | Quote not verbatim in the local source after the normalisation of section 3. Outcome `FOUND` (with SHA-256 and offsets), `NOT_FOUND`, or `UNCHECKABLE` (no local text) |
| W1 | A number in the claim or span that is absent from the quote or cited passage (number overreach) |
| W2 | A certainty upgrade from quote to claim, from a fixed, published word list (hedged to assertive, for example "may", "suggests", "associated" to "shows", "causes", "proves"). Opt-in (`--with-w2`) since 0.2.0: on a hand-checked sample only about a third of its flags were real overreach |
| T1 | Theorizer: an evidence ID cited by a law that resolves to no evidence record |
| T2 | Theorizer: a law with an empty scope or an empty evidence list |

**Outputs**: exit code 0 or 1 (1 on any `E` code); GitHub annotation lines; the JSON
report of section 3 with every finding's receipt.

**Packaging**: a CLI; a Python API; a Claude Code plugin in the asta-plugins marketplace
layout (`plugins/consilience-receipts/skills/evidence-receipts/SKILL.md` and a script);
a documented `workspace.mk` target so a project can add the check to `make check`.

**Validation (all deterministic)**
1. Seeded-defect workspace suite: a synthetic Asta-format workspace with every E and W
   code planted at known lines, plus clean controls. Target, by construction and as a
   unit test: every planted defect found, no finding on the clean controls.
2. Theorizer released corpus (2,856 theories and about 16 thousand evidence records):
   the T1 rate, the T2 rate, and the W1 and W2 rates between each law and its cited
   evidence text, each with n, examples with receipts, and parse coverage. Whether these
   rates differ between theories with high and low released predictive-accuracy counts
   is reported as exploratory.
3. SciArena-Eval (2,000 votes, 31,845 inline citations with passages): the citation
   resolution rate, the W1 and W2 rates per citation, and whether responses with more
   W1/W2 flags lose human votes more often. That last comparison is preregistered by
   commit before it is computed; a null is reported as a null.

**Done when** the seeded suite passes, the Theorizer and SciArena results are in the
registry with receipts, the plugin layout is validated by a test, and the `make check`
integration is documented and tested on the synthetic workspace.

### C2. Experiment audit (`consilience-ai2 audit`)

**Inputs (adapters)**
- AutoDiscovery: `mcts_node_*.json` or `mcts_nodes_all.json`, plus `args.json` and the
  dataset metadata; or a hosted run's `results.json`. Per node: `id`, `hypothesis`,
  `experiment_plan.{objective, steps, deliverables}`, `code`, `code_output`, `analysis`,
  `review`, `success`, `prior.mean`, `posterior.mean`, `belief_change`, `surprising`. No
  run outputs are public, so this adapter is tested on schema-faithful synthetic
  fixtures generated from the released dataclasses (`MCTSNode.to_dict`), labelled
  synthetic.
- CodeScientist experiment directories: plan, code, logs, `results.json`, report.
- DiscoveryBench tasks: CSV plus metadata (for A5).

**Checks**

| Code | Rule |
|---|---|
| A1 | Number receipt: every number in the analysis or report appears in the code output or results file at the printed precision |
| A2 | Stated n vs printed n vs n constants in the code |
| A3 | Columns named in the code or hypothesis but absent from the dataset metadata |
| A4 | "Surprising" or "significant" with no test statistic or p-value printed |
| A5 | Benjamini–Hochberg across all p-values parsed from a run; q per node; flag surprising nodes with q > 0.05; report parse coverage |
| A6 | Surprising null, paired with the minimum detectable effect from n |
| A7 | Effect size present |
| R1 | Random-only baseline: the only comparator is random or chance |
| R2 | Rerun instability (when reruns exist): the verdict flips across reruns |
| R3 | Sample-size floor for a stated claim (power-based, documented) |
| R4 | Hard-coded result: the result literal appears in the code as a constant assigned to the output |
| R5 | Built-but-unused: a declared component is never referenced on the result path. Implemented only if a static analysis can be done honestly; otherwise reported as `not implemented` |

**Outputs**: `validity_audit.json`, version 1:

```json
{"version": 1, "run": "<out_dir or run_id>", "n_nodes": 0, "n_with_pvalue": 0,
 "nodes": [{"id": "node_3_1",
            "llm_validity_check": {"success": true, "text_sha256": "…"},
            "checks": [{"code": "A1", "severity": "error", "field": "analysis",
                        "span": "<as written>", "message": "…"}],
            "q_value": null, "verdict": "flag"}]}
```

A per-node verdict of `pass`, `flag` or `refuse`, with codes, receipts and q values. The
existing review text is hashed alongside.

**Packaging**: a CLI and an API; a Claude Code plugin skill (`consilience-audit`); a
documented post-run hook for AutoDiscovery; an optional wrapper, shipped as an example,
that adds a `deterministic_checks` field to each node before the nodes are saved.

**Validation**
1. Development set: the CodeScientist human verdicts on 19 reported discoveries (6
   accepted, 13 rejected, with reasons). Per rejection reason, whether the audit flags
   it, and false flags on the accepted ones. Labelled `dev`: the reasons are public and
   the rules were written knowing them.
2. Held-out, preregistered: the 50-idea meta-analysis (50 ideas × 5 runs, verdict
   consistency) and the 60 external ratings. A preregistration file names the
   hypothesis first: runs the audit flags have lower verdict consistency across reruns,
   and lower external ratings, than runs it passes. It is then scored with a stated test
   and a permutation null. Rules are frozen at the preregistration commit.
3. A5 on the DiscoveryBench synthetic tasks: a fixed deterministic scan of every column
   against the target, with a documented test per variable type; false discoveries
   among distractor columns (those outside the gold relation) counted with and without
   Benjamini–Hochberg; the reduction reported with n.
4. Reproduction of a published number: the CodeScientist resistor report's success-rate
   table reproduces exactly from its `results.json`, as a test.

### C3. Reproduction verdict (`consilience-ai2 reproduce`)

**Input**: a reproduction record (YAML or JSON) following the asta-flows secondary
reproduction rubric:
- the source claim: quantity, value, unit, n, effect size, conditions;
- the reproduction: quantity, value, unit, n, conditions;
- committed thresholds (equivalence margin and/or minimum effect) with their commit
  hash and time;
- the result commit hash and time.

**Checks**

| Code | Rule |
|---|---|
| F1 | Faithfulness: `same_quantity`, `proxy`, `substitution` or `not_comparable(<condition>)`, from a declared mapping, with named condition mismatches, unit handling and fail-closed parsing (via the optional `consilience` package where it fits) |
| D1 | Decidability: `underpowered` (power at the source effect size from n, below a threshold), `no_data`, `not_identifiable`; otherwise `decidable` |
| V1 | Verdict from numbers only: `reproduced`, `not_reproduced` or `inconclusive`, against the committed thresholds |
| P1 | Commit order: thresholds committed before the result (git timestamps); otherwise `thresholds_post_hoc` |
| P2 | The hypothesis text is a verbatim copy of the source claim |

**Outputs**: `reproduction_verdict.json` with codes and receipts.

**Packaging**: a CLI, an API, a `verdict.py` drop-in example for the asta-flows workflow
pattern, and a Claude Code plugin skill.

**Validation**
1. CodeScientist reruns as reproductions: for ideas with at least 2 completed runs, run
   1 is the source and runs 2..k are reproductions. Reported: the distribution of
   verdicts and decidability classes, and agreement with CodeScientist's own
   consistency labels.
2. DiscoveryBench synthetic tasks with planted effects and nulls, reproduced on held-out
   row halves: verdicts on planted effects mostly `reproduced`, on nulls mostly
   `not_reproduced` or `inconclusive`, and underpowered splits classed `underpowered`.
3. Unit tests for the P1 commit-order logic on a scratch git repository.

## 5. Repository layout

```
consilience_ai2/            package
  core/                     hashing, normalisation, numbers, findings, CLI registry, results
  receipts/                 C1
  audit/                    C2
  reproduce/                C3
  fetch/                    pinned downloads (URLs + SHA-256 or commit); never committed data
.claude-plugin/             marketplace.json (asta-plugins layout)
plugins/                    Claude Code plugins, one directory per plugin
examples/                   synthetic Asta workspace with seeded defects; AutoDiscovery
                            schema fixtures; reproduction records
analyses/                   scripts that produce results on fetched data
prereg/                     preregistration files, committed before the scoring commit
results/                    <component>.json, registry.json, NUMBERS_LOCK.json
docs/                       SPEC.md, RESULTS.md, LIMITATIONS.md, INTEGRATION.md
tests/                      unit and fixture tests (no network)
README.md NOTICE LICENSE (MIT) CHANGELOG.md CONTRIBUTING.md
```

CI (GitHub Actions) runs on every push and pull request: ruff, pytest, the numbers lock,
the marketplace consistency check and a secret, data and model-identifier scan.
Requires Python 3.11 or newer. Runtime dependencies: PyYAML, numpy and scipy;
`consilience` (PyPI) is an optional extra for comparability.

## 6. Integration points (file formats and hooks)

| Tool | Hook | Format |
|---|---|---|
| receipts | A step in a workspace's `make check`, through a project-owned `workspace.mk` target; or the `evidence-receipts` plugin skill | Reads the workspace files; writes the report JSON and GitHub annotation lines in the style of the workspace's `quarto-check.sh` |
| audit | A post-run command on an AutoDiscovery output directory; or the `consilience-audit` plugin skill | Reads `mcts_node_*.json` / `mcts_nodes_all.json`, `args.json` and the dataset metadata (or a hosted `results.json`); writes `<out_dir>/validity_audit.json` |
| audit | Optional in-run wrapper (an example, not a patch) | Adds a `deterministic_checks` field to each node dict before the nodes are saved |
| reproduce | A `verdict.py` script beside the secondary-reproduction workflow, in the pattern of its `check.py` and `runlog.py` | Reads the reproduction record; writes `reproduction_verdict.json` |

## 7. Data sources

`consilience-ai2 fetch --list` shows every source; `consilience_ai2/fetch/sources.yaml`
holds each pin, licence and citation.

| Name | Kind | Pin |
|---|---|---|
| `codescientist` | git | commit 778b146 |
| `codescientist-example-experiments` | file (zip, extracted) | SHA-256 21d2b985… |
| `codescientist-full50` | file (zip, read in place) | SHA-256 e0cd9d5a… |
| `theorizer-paper-data` | file (zip, extracted) | SHA-256 be0fe473… |
| `asta-theorizer` | git | commit c4802aa |
| `sciarena-eval` | file (JSON) | SHA-256 fb0e5b44…, dataset revision e208515 |
| `discoverybench` | git | commit c31fcf0 |
| `asta-autodiscovery` | git | commit 30e080f |
| `asta-plugins` | git | commit a2dcade |
