# consilience-ai2

Deterministic validity checks for agent-produced science, built for the file formats of
Ai2's Asta stack and tested on Ai2's released data.

**Independent work, not affiliated with or endorsed by the Allen Institute for AI (Ai2).**

Three rule-based tools: no model calls, and the same input gives byte-identical output.
Every finding carries a **receipt**, the SHA-256 of the source it checked plus the file
and line or the character offsets. Passing checks emit receipts too. An input that
cannot be decided is reported as `UNCHECKABLE` / `refuse`, never guessed or skipped.

| Command | Checks | Reads |
|---|---|---|
| `consilience-ai2 receipts check` | Is every quote real, resolvable and verbatim, and does the claim overstate it in number or in certainty? | an Asta workspace: `evidence.yml`, `.qmd` `.ev` spans, `references.bib` |
| `consilience-ai2 audit run` | Do the reported numbers come from the run? Is the n right? Is there a real test, an effect size, a real baseline, and control for many tests? | AutoDiscovery `mcts_node_*.json` / `mcts_nodes_all.json` or a hosted `results.json`; CodeScientist experiment directories |
| `consilience-ai2 reproduce check` | Is the reproduction the same quantity, could it decide at all, and what do the numbers say against thresholds committed in advance? | a reproduction record (YAML/JSON) per the asta-flows secondary-reproduction rubric |

Design and every check code: [docs/SPEC.md](docs/SPEC.md). Hook points and JSON
schemas: [docs/INTEGRATION.md](docs/INTEGRATION.md).

## Install

```bash
pip install "git+https://github.com/Anuja-Khatri/consilience-ai2"
# optional: unit-aware comparability for `reproduce` (the consilience package)
pip install "consilience-ai2[consilience] @ git+https://github.com/Anuja-Khatri/consilience-ai2"
```

Python 3.11 or newer. Runtime dependencies: PyYAML, numpy, scipy. The quickstarts below
run on synthetic examples shipped in the repository, so run them from a clone:

```bash
git clone https://github.com/Anuja-Khatri/consilience-ai2 && cd consilience-ai2
pip install .
```

## The three tools

### Evidence receipts

Checks an asta-plugins workspace as Quarto and its evidence filter read it: unknown
`.ev` keys (E1), spans with no quote (E2), `cite` keys missing from the bibliography
(E3), orphaned entries (E4), malformed `provenance` (E5: an exact `asta` subcommand, an
integer `corpus_id`, an http/https/asta URL, an ISO date), and whether each quote is
verbatim in local source text after a fixed, versioned normalisation (E6: `FOUND` with
SHA-256 and offsets, `NOT_FOUND`, or `UNCHECKABLE` without local text). Two warnings:
a number in the claim that the quote does not support (W1) and an assertive claim over
a hedged quote, from a fixed word list (W2). Adapters read Theorizer's released export
(T1 dangling evidence IDs, T2 empty scope or evidence) and SciArena-Eval citations.

```bash
consilience-ai2 receipts check examples/receipts/seeded \
    --sources examples/receipts/seeded/sources --json /tmp/receipts.json
```

```text
::error file=defects.qmd,line=7::E1 .ev span references unknown key "d-missing-key"
::error file=defects.qmd,line=23::E6 NOT_FOUND: the quote is not verbatim in file:smith2024.txt
::warning file=defects.qmd,line=29::W2 certainty upgrade: claim says causes; quote says may, associated
::error file=evidence.yml,line=66::E5 provenance.method 'asta search papers' is not an exact asta subcommand
...
receipts: 26 spans, 20 entries; 14 errors, 3 warnings, 22 receipts
```

Exit code 1 (errors). The clean workspace, `examples/receipts/clean`, passes with exit
code 0. A receipt in the JSON report:

```json
{"code": "E6", "severity": "info", "file": "controls.qmd", "line": 8, "key": "c-ligature",
 "message": "FOUND in file:smith2024.txt at [231, 280)",
 "receipt": {"source": "file:smith2024.txt", "sha256": "4405fe979d5bd14a7e1024e36da67043b1d82c2ae2debd4646fab31c4284c718",
             "offset": 231, "end": 280, "normalisation": "consilience-ai2.normalise/1"}}
```

Doc: [docs/receipts.md](docs/receipts.md).

### Experiment audit

Audits each experiment ("node") of an AutoDiscovery run or a CodeScientist experiment
directory: every reported decimal printed in the output or code at the printed
precision (A1), the stated n (A2), columns in the dataset metadata (A3), "significant"
or "surprising" with a printed test (A4), Benjamini–Hochberg q across all the run's p
values (A5), the minimum detectable effect of a surprising null (A6), an effect size
(A7), random-only comparators (R1), rerun flips (R2), a power-based n floor (R3),
hard-coded result literals (R4) and built-but-unused components by static analysis
(R5). Each node gets `pass`, `flag` or `refuse`. AutoDiscovery's own language-model
"Validity Check" is hashed and kept beside the verdict, not judged.

```bash
consilience-ai2 audit run examples/audit/autodiscovery/synthetic_run --json /tmp/validity_audit.json
```

```text
node_2_0: pass ...
node_2_1: refuse ... A1
...
node_2_4: flag A4
...
node_2_11: refuse U1
::error file=mcts_node_2_1.json,line=1::A1 0.42 is not printed in the run's output or code at the printed precision
::error file=mcts_node_2_10.json,line=5::R5 function 'build_interaction_features' is used but nothing it computes reaches any printed or saved output
::error file=mcts_node_2_3.json,line=5::A3 column 'household_size' is read by the code but is not in the dataset metadata
::error file=mcts_node_2_8.json,line=1::R1 the only comparator named is random or chance
...
audit: 12 nodes, 1 pass, 8 flag, 3 refuse; p values parsed for 10; wrote /tmp/validity_audit.json
```

One line per node (`<id>: pass|flag|refuse q=<q> <codes>`, with `...` above standing
for the q values and the lines left out), then GitHub annotation lines, then a summary.
Exit code 1 (error-severity findings).

The run in `examples/audit/autodiscovery/` is **synthetic**: no AutoDiscovery run outputs
are public, so it was written from the released node schema with one defect planted per
node. Doc: [docs/audit.md](docs/audit.md).

### Reproduction verdict

Turns the verdict rubric of the asta-flows "Secondary reproduction" workflow into code
that reads only the numbers in a structured record: faithfulness (F1: same quantity,
proxy, substitution, or not comparable), decidability (D1: power at the source effect
from the reproduction's n; underpowered, no data, not identifiable), the verdict
against the committed thresholds (V1: reproduced, not reproduced, inconclusive), whether
the thresholds were committed before the result in git (P1), and whether the hypothesis
was copied verbatim (P2).

```bash
consilience-ai2 reproduce check examples/reproduce/records/supported.yaml --json /tmp/verdict.json
```

```text
::notice file=supported.yaml,line=5::P2 hypothesis copy: verbatim
::notice file=supported.yaml,line=16::D1 decidability: decidable
::notice file=supported.yaml,line=16::F1 faithfulness: same_quantity
::error file=supported.yaml,line=26::P1 commit order: thresholds_post_hoc (same_commit)
::notice file=supported.yaml,line=26::V1 verdict from the numbers: reproduced (supported)
{"decidability": "decidable", "faithfulness": "same_quantity", "outcome_label": "supported", "verdict": "reproduced"}
wrote /tmp/verdict.json
```

The numbers support the reproduction, and the run still exits 1: the example record was
committed with its thresholds and its result in the same commit, so P1 cannot credit
the thresholds as fixed first. In a real run, commit the thresholds before the result.
The other records in `examples/reproduce/records/` show an underpowered test, a
substitution, a proxy that is rejected, and a unit mismatch. Doc:
[docs/reproduce.md](docs/reproduce.md).

## Results on Ai2's released data

Every number below renders from [`results/registry.json`](results/registry.json); CI
fails if one does not. Labels: **held-out** = preregistered by commit before scoring;
**dev** = the rules were written knowing these data; **exploratory**, **descriptive**
(a measured rate, no hypothesis) and **synthetic** (true by construction). Full table
with n, intervals and sources: [docs/RESULTS.md](docs/RESULTS.md).

| Tool | Data | Result | n | Label |
|---|---|---|---|---|
| receipts | SciArena-Eval votes | **Null.** The response with the higher W1+W2 flag rate lost the human vote in 50.09% of votes (95% CI 45.9% to 54.27%), sign-test p = 1.0 | 569 | held-out |
| receipts | Theorizer laws (released export) | T1: 1.36% of cited (law, evidence ID) pairs resolve to no evidence record, all through the export's fallback link | 14343 | descriptive |
| receipts | Theorizer laws | T2: 0.88% of laws have an empty scope and an empty evidence list, all in the parametric accuracy-focused condition | 4187 | descriptive |
| receipts | Theorizer laws | W1: 37.78% state a number absent from their cited records; 84.62% in the novelty-focused condition, whose laws are quantitative predictions by design | 1887 | descriptive |
| receipts | SciArena-Eval citations | all but one of 31820 inline citations resolve to a listed passage; W1 1.42% and W2 1.4% of resolved citations | 31819 | descriptive |
| receipts | seeded synthetic workspace | 100% of planted defects found, 0 findings on the clean controls | 17 | synthetic |
| audit | CodeScientist full-50 reruns | H1 **not supported in the predicted direction**: runs the audit flags agreed more with their reruns (0.4408) than runs it passed (0.3433); stratified permutation p = 0.0845 | 80 | held-out |
| audit | CodeScientist external ratings | H2 **null**: soundness 0.6296 flagged against 0.6667 passed, p = 0.8561 (same papers as the dev set) | 20 | exploratory |
| audit | CodeScientist Table 4 discoveries | 9 of 13 rejected discoveries flagged by a code meant for the reviewers' reason; 3 of 6 accepted carry an error-severity code | 19 | dev |
| audit | DiscoveryBench synthetic tasks (A5) | Benjamini–Hochberg cuts distractor-column hits from 7.43% to 2.74% of tests (63.14% fewer); with a permuted target, tasks with any hit fall from 73.25% to 3.82% | 4456 tests | descriptive / synthetic |
| audit | CodeScientist resistor report | its success-rate table reproduces exactly from its `results.json`, 9 of 9 cells | 9 | descriptive |
| reproduce | CodeScientist reruns as reproductions | numbers recoverable in both runs for 36.92% of pairs (95% CI 26.23% to 49.08%); verdicts 4 reproduced, 0 not reproduced, 61 inconclusive; 27.69% agreement with CodeScientist's own run labels | 65 | descriptive |
| reproduce | DiscoveryBench planted effects and nulls, held-out row halves | nulls not reproduced or inconclusive 97.77%; planted effects reproduced 47.77% overall and 96.61% where D1 calls the test decidable | 1569 / 358 / 177 | synthetic |

What these do not show is in [docs/LIMITATIONS.md](docs/LIMITATIONS.md). In short: no
real AutoDiscovery run is public, so the AutoDiscovery adapter is tested on synthetic
fixtures only; the audit's dev set is not blind and its held-out prediction failed;
W1/W2 are lexical; E6 needs local source text; parsing is regex-level; DiscoveryBench's
planted/null labels are impure; samples are small; and most CodeScientist rerun pairs
lack the numbers a verdict needs.

## Data

Nothing from Ai2 is redistributed here beyond short excerpts quoted as receipts. Fetch the
released data yourself, pinned and verified:

```bash
consilience-ai2 fetch --list          # sources, pins and cache status
consilience-ai2 fetch all             # into ~/.cache/consilience-ai2 (or $CONSILIENCE_AI2_DATA)
consilience-ai2 fetch all --from-dir /path/with/copies --offline   # from local copies
```

Each file is checked against its SHA-256 and each git repository against its commit; a
mismatch is refused. Then the analyses reproduce `results/*.json` byte for byte (with
the same numpy and scipy versions):

```bash
python analyses/receipts/run.py
python analyses/audit/run_all.py
python analyses/reproduce/run.py
make lock        # registry, results table and numbers lock
```

Sources, licences and citations: `consilience_ai2/fetch/sources.yaml` and
[NOTICE](NOTICE).

## Claude Code plugins

The repository is a plugin marketplace in the asta-plugins layout. In Claude Code:

```text
/plugin marketplace add Anuja-Khatri/consilience-ai2
/plugin install consilience-receipts@consilience-ai2
/plugin install consilience-audit@consilience-ai2
/plugin install consilience-reproduce@consilience-ai2
```

or from a shell, `claude plugin marketplace add Anuja-Khatri/consilience-ai2` and
`claude plugin install <plugin>@consilience-ai2`. The skills (`evidence-receipts`,
`experiment-audit`, `reproduction-verdict`) run the `consilience-ai2` command, so
install the package too. `evidence-receipts` ships a snippet that adds the check to a
workspace's `make check` ([docs/INTEGRATION.md](docs/INTEGRATION.md)).

## Development

```bash
make setup     # .venv with the package in editable mode and the dev tools
make ci        # ruff, pytest (no network), numbers lock, marketplace check, secret scan
```

Contributor rules: [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [CHANGELOG.md](CHANGELOG.md).

## Licence

MIT (see [LICENSE](LICENSE)). Credits for every third-party artefact, with licences and
pinned commits: [NOTICE](NOTICE).

Independent work, not affiliated with or endorsed by the Allen Institute for AI (Ai2).
