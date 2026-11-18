# consilience-ai2

Rule-based checks for the outputs of AI research agents, built to work with the file
formats of Ai2's Asta tools and tried on data that Ai2 and its collaborators have openly
released.

**Independent work, not affiliated with or endorsed by the Allen Institute for AI (Ai2).**

## What this is

Ai2 has released an unusually open set of tools and data for AI-assisted science: the
Asta agents and research skills, Theorizer, CodeScientist, AutoDiscovery, DiscoveryBench
and SciArena. This project is built on top of that openness. It would not be possible
without it.

It offers one small, complementary piece: **rule-based checks that sit beside the model
reviewers already in these tools**. They give the same answer every time, call no language
model, and show exactly what they checked, in a *receipt*. They are meant to help, not to
replace any existing step or to grade anyone's work.

Asta is Ai2's set of agents and research skills for science. The three tools here read
Asta's file formats as they are.

## The three tools at a glance

| Command | The question it helps answer | You give it | You get back |
|---|---|---|---|
| `consilience-ai2 receipts check` | Is each quoted piece of evidence word for word in its source, and does the claim stay within it in number and in certainty? | an Asta workspace (`evidence.yml`, `.qmd` files, `references.bib`) and, if you have them, the source texts | one note per item to look at, a receipt for every quote checked, a JSON report |
| `consilience-ai2 audit run` | Do the numbers in an experiment's write-up appear in the run's output, and are the basic statistical checks in place: the n, a test, a baseline, control for many tests? | an AutoDiscovery run directory or a CodeScientist experiment directory | a result per experiment (`pass`, `flag` or `refuse`) with receipts, in `validity_audit.json` |
| `consilience-ai2 reproduce check` | Does a reproduction measure the same thing as the original, could it decide at all, and do its numbers meet thresholds fixed in advance? | a reproduction record (YAML or JSON) | `reproduced`, `not reproduced` or `inconclusive`, with the reason, in `reproduction_verdict.json` |

AutoDiscovery is Ai2's agent that explores a dataset by proposing and testing hypotheses.

A **receipt** is the file and line (or the character offsets) of what was checked, plus
the SHA-256 fingerprint of that exact source, so anyone can confirm which bytes were
checked. Passing checks get receipts too. When an input cannot be decided, the tools say
so rather than guess: a quote with no local source text is `UNCHECKABLE`, and an
experiment with nothing to check gets the result `refuse`. The same input always gives
byte-identical output.

## What we learned by running it on released data

To test the tools honestly, we ran them on data Ai2 and its collaborators have published.
Our own limits come first.

- **Our tools have real limits.** Two preregistered tests did not support our
  predictions. (A *preregistered* test is one whose hypothesis and decision rule were
  committed to git before any scoring.) On SciArena-Eval, a released set of human votes
  between two AI answers to the same science question, answers with more flagged
  citations did not lose the vote more often (null). On CodeScientist reruns, runs our
  audit flagged agreed *more* with their reruns, not less (not significant). A third test
  could not be run, because too few runs were flagged. On a hand-checked sample, only
  about half of our number flags were real. [Results](docs/RESULTS.md#preregistered-held-out-tests)
- **Theorizer's released export: a small number of evidence links did not resolve.**
  Theorizer generates scientific theories whose laws cite evidence records. In the
  released export, 195 of 14,343 cited evidence links (1.36%) point to a page that is not
  in the export; the export script quietly keeps an ID it cannot match as a link. We
  could not tell why those IDs are unmatched, and it may be a packaging detail.
  [Details](docs/receipts.md#t1-theorizer-evidence-links-that-point-to-missing-records)
- **CodeScientist's released experiments: two small details a rule-based check can
  catch.** CodeScientist designs, runs and writes up code experiments. In two discoveries
  from the paper's released set, a reported standard deviation (15.8%) does not appear in
  the run's output (recomputed from the run's data it is 16.2%), and one write-up uses
  "significantly" without a printed test. These are the kind of small details that are
  easy to miss by eye; our rules were written while looking at these data (label: dev).
  [Details](docs/audit.md#development-set-codescientist-table-4-labelled-dev-not-blind)
- **DiscoveryBench: standard multiple-testing control helps a simple scan.** On
  DiscoveryBench's synthetic tasks, a Benjamini–Hochberg correction (a standard
  adjustment of p values when many tests are run) cut chance hits among unrelated
  "distractor" columns from 7.43% to 2.74% of tests; with the target shuffled, so that
  every hit is false, the share of tasks with any hit fell from 73.25% to 3.82%.
  [Details](docs/audit.md#a5-on-discoverybench-synthetic-tasks-labelled-descriptive-null-control-synthetic)

All of this is shared in the hope that it is useful. Corrections and suggestions are very
welcome.

## Try it in two minutes

The examples ship with the repository, so run them from a clone (Python 3.11 or newer):

```bash
git clone https://github.com/Anuja-Khatri/consilience-ai2 && cd consilience-ai2
pip install .

# 1. Evidence receipts, on a synthetic workspace with planted defects
consilience-ai2 receipts check examples/receipts/seeded --sources examples/receipts/seeded/sources

# 2. Experiment audit, on a synthetic AutoDiscovery run
consilience-ai2 audit run examples/audit/autodiscovery/synthetic_run --json /tmp/validity_audit.json

# 3. Reproduction verdict, on an example record
consilience-ai2 reproduce check examples/reproduce/records/supported.yaml --json /tmp/verdict.json
```

What the output means:

1. Each `::error` or `::warning` line names a file, a line and a check code. GitHub
   shows these lines inline on a pull request. The last line counts the spans, errors,
   warnings and receipts. The defects were planted on purpose, so the exit code is 1.
   The clean workspace, `examples/receipts/clean`, passes with exit code 0.
2. One line per experiment: `pass`, `flag(warning)`, `flag(error)` or `refuse`, then its
   q value (its p value adjusted for many tests) and the codes that fired. The synthetic run has
   one clean experiment, one with nothing to check, and one planted defect in each of
   the others.
3. The verdict is `reproduced`, yet the run exits 1. The example record was committed
   with its thresholds and its result together, so the tool cannot credit the thresholds
   as fixed first. `python examples/reproduce/demo_commit_order.py` shows the passing
   case.

Each tool is explained in detail [below](#the-three-tools-in-detail).

## How to read the results

Every result number in this repository is computed by a script, from released data or
from synthetic fixtures, stored in [`results/registry.json`](results/registry.json), and checked against the docs
in CI. Each result carries a label. **Held-out**: the prediction was written down and
committed before looking at the data it was scored on. **Dev**: the rules were written
while looking at these data, so the result shows fit, not generalisation. **Synthetic**:
made-up data where the right answer is known, so the result shows that the rules do what
they say. **Descriptive**: a measured rate, with no hypothesis. **Exploratory**: computed
and reported, but not used to decide anything.

## What it does not do

- **It does not judge meaning.** The claim checks compare numbers and words. On a
  hand-checked sample, about half of the number flags and about a third of the certainty
  flags were a real overreach.
- **It cannot check a quote without the source text.** Without local text, a quote is
  `UNCHECKABLE`.
- **It has not been run on a real AutoDiscovery run.** None is public, so the
  AutoDiscovery support is tested on synthetic files written from the released format.
- **It has not shown that its flags predict replication.** That preregistered
  prediction failed, and the follow-up test could not be run.
- **It reads text with fixed patterns.** It catches wording, not intent, and misses
  defects phrased in unusual ways.
- **Its samples are small.** Most CodeScientist rerun pairs also lack the numbers a
  reproduction verdict needs.

The full list is in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Install

```bash
pip install "git+https://github.com/Anuja-Khatri/consilience-ai2"
# optional: unit-aware comparability for `reproduce` (the consilience package)
pip install "consilience-ai2[consilience] @ git+https://github.com/Anuja-Khatri/consilience-ai2"
```

Python 3.11 or newer. Runtime dependencies: PyYAML, numpy, scipy. The examples above need
a clone of the repository.

The design and every check code are in [docs/SPEC.md](docs/SPEC.md). Hook points and JSON
schemas are in [docs/INTEGRATION.md](docs/INTEGRATION.md).

## The three tools in detail

Each check has a short code, such as `E6` or `A1`. The code appears in every finding, so
a finding can be looked up in the tool's document.

### Evidence receipts

This tool checks an asta-plugins workspace: a Quarto project in which claims are marked
with `.ev` spans that point to stored quotes. asta-plugins is Ai2's repository that
distributes Asta's research skills as agent plugins. The checker reads the workspace as Quarto and the asta-plugins
evidence filter read it.

Errors (they fail the run):

- **E1**: a `.ev` span names a key that is not in the evidence store.
- **E2**: a span has no quote.
- **E3**: a `cite` key is missing from the bibliography.
- **E4**: an evidence entry is used by no span.
- **E5**: the `provenance` is malformed. Each field that is present must be valid: an
  exact `asta` subcommand, an integer `corpus_id`, an http, https or asta URL, an ISO
  date.
- **E6**: the quote is not word for word in the local source text, after a fixed,
  versioned normalisation. The outcome is `FOUND` (with the SHA-256 and offsets),
  `NOT_FOUND`, or `UNCHECKABLE` when there is no local text.

Warnings:

- **W1** (on by default): the claim states a number that the quote does not support.
- **W2** (opt-in, `--with-w2`): the claim is assertive where the quote is hedged, judged
  from a fixed word list.

W2 is opt-in because on a hand-checked sample only about a third of its flags were real
overreach (W1: about half). The W1 and W2 rules v0.2 are the default; `--rules v0.1`
selects the frozen rules of the preregistered SciArena test. Adapters also read
Theorizer's released export (T1: cited evidence IDs with no record; T2: laws with an empty
scope or an empty evidence list) and SciArena-Eval citations.

```bash
consilience-ai2 receipts check examples/receipts/seeded \
    --sources examples/receipts/seeded/sources --json /tmp/receipts.json
```

```text
::error file=defects.qmd,line=7::E1 .ev span references unknown key "d-missing-key"
...
::error file=defects.qmd,line=23::E6 NOT_FOUND: the quote is not verbatim in file:smith2024.txt
::warning file=defects.qmd,line=25::W1 number in the claim not in the quote: 91.2%25
...
::error file=evidence.yml,line=66::E5 provenance.method 'asta search papers' is not an exact asta subcommand
...
receipts: 26 spans, 20 entries; 14 errors, 2 warnings, 22 receipts
```

`%25` is how a GitHub annotation escapes `%`. Add `--with-w2` to also get the planted
certainty upgrade (`::warning file=defects.qmd,line=29::W2 certainty upgrade: claim says
causes; quote says may, associated`; 3 warnings). The exit code is 1, because there are
errors. The clean workspace, `examples/receipts/clean`, passes with exit code 0. A receipt
in the JSON report:

```json
{"code": "E6", "severity": "info", "file": "controls.qmd", "line": 8, "key": "c-ligature",
 "message": "FOUND in file:smith2024.txt at [231, 280)",
 "receipt": {"source": "file:smith2024.txt", "sha256": "4405fe979d5bd14a7e1024e36da67043b1d82c2ae2debd4646fab31c4284c718",
             "offset": 231, "end": 280, "normalisation": "consilience-ai2.normalise/1"}}
```

Full document: [docs/receipts.md](docs/receipts.md).

### Experiment audit

This tool audits each experiment ("node") of an AutoDiscovery run or a CodeScientist
experiment directory. It asks whether the numbers in the write-up come from the run and
whether the statistics hold up. The checks:

- **A1**: every reported decimal is printed in the run's output or code, at the printed
  precision.
- **A2**: a stated sample size (n) is printed by the run or set in the code.
- **A3**: the columns the code reads are in the dataset metadata.
- **A4**: "significant" or "surprising" comes with a printed test.
- **A5**: Benjamini–Hochberg q values across all the run's p values, which control for
  running many tests.
- **A6**: the smallest effect that a "surprising" null result could have detected.
- **A7**: an effect size is reported (an info note in v0.2).
- **R1**: the only comparator is random or chance.
- **R2**: reruns of the same idea flip the result.
- **R3**: the sample is below a power-based floor.
- **R4**: result values are hard-coded in the code.
- **R5**: a component is built but nothing it computes reaches an output (found by static
  analysis).

Each node gets `pass`, `flag` or `refuse`. AutoDiscovery's own language-model "Validity
Check" is hashed and kept beside the verdict, not judged.

```bash
consilience-ai2 audit run examples/audit/autodiscovery/synthetic_run --json /tmp/validity_audit.json
```

```text
node_2_0: pass ...
node_2_1: flag(error) ... A1
...
node_2_4: flag(error) A4
...
node_2_11: refuse U1
...
::error file=mcts_node_2_1.json,line=1::A1 0.42 is not printed in the run's output or code at the printed precision
::error file=mcts_node_2_10.json,line=5::R5 function 'build_interaction_features' is used but nothing it computes reaches any printed or saved output
...
::error file=mcts_node_2_3.json,line=5::A3 column 'household_size' is read by the code but is not in the dataset metadata
...
::error file=mcts_node_2_8.json,line=1::R1 the only comparator named is random or chance
...
audit (audit-rules-2): 12 nodes, 2 pass, 3 flag(warning), 6 flag(error), 1 refuse; p values parsed for 10; wrote /tmp/validity_audit.json
```

The output is one line per node (`<id>: pass|flag(warning)|flag(error)|refuse q=<q>
<codes>`; `...` above stands for the q values and the lines left out), then GitHub
annotation lines, then a summary. The exit code is 1, because there are error-severity
findings. The rules are v0.2 (`audit-rules-2`): severities recalibrated on the
development set, A7 (no effect size) an info note, A1 tiers, R2 split.

The run in `examples/audit/autodiscovery/` is **synthetic**. No AutoDiscovery run
outputs are public, so it was written from the released node schema, with one defect
planted per node. Full document: [docs/audit.md](docs/audit.md).

### Reproduction verdict

asta-flows is a set of research workflows in asta-plugins. Its "Secondary reproduction"
workflow has a written rubric for deciding whether a result reproduced. This tool turns
that rubric into code. It reads only the numbers in a structured record:

- **F1, faithfulness**: is the reproduction the same quantity, a proxy, a substitution,
  or not comparable?
- **D1, decidability**: could the test decide at all? This is the power at the source
  effect, given the reproduction's n. The outcomes are decidable, underpowered, no data
  and not identifiable.
- **V1, verdict**: reproduced, not reproduced or inconclusive, against the thresholds
  committed in advance.
- **P1, commit order**: were the thresholds committed before the result, in git?
- **P2, hypothesis copy**: was the hypothesis copied word for word?

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

The numbers support the reproduction, and the run still exits 1. The example record was
committed with its thresholds and its result in the same commit, so P1 cannot credit the
thresholds as fixed first. In a real run, commit the thresholds before the result. The
demo does this: it builds a scratch git repository, commits the plan and thresholds
first and the result second, and exits 0.

```bash
python examples/reproduce/demo_commit_order.py
```

```text
c1f75ef plan: test and thresholds, before the run
a75b596 result: reproduction numbers
::notice file=committed_first.yaml,line=3::P2 hypothesis copy: verbatim
::notice file=committed_first.yaml,line=19::D1 decidability: decidable
::notice file=committed_first.yaml,line=19::F1 faithfulness: same_quantity
::notice file=committed_first.yaml,line=35::P1 commit order: committed_first
::notice file=committed_first.yaml,line=35::V1 verdict from the numbers: reproduced (supported)
{"decidability": "decidable", "faithfulness": "same_quantity", "outcome_label": "supported", "verdict": "reproduced"}
wrote reproduction_verdict.json
exit 0
```

Since v0.2, the verdict reads the source's finding: the expected direction is the sign of
the source effect (`--rule v0.1` uses the declared direction). The other records in
`examples/reproduce/records/` show an underpowered test, a substitution, a proxy that is
rejected, and a unit mismatch. Full document: [docs/reproduce.md](docs/reproduce.md).

## Results on Ai2's released data

Every number below renders from [`results/registry.json`](results/registry.json); CI
fails if one does not. Labels: **held-out** = preregistered by commit before scoring;
**dev** = the rules were written knowing these data; **exploratory**, **descriptive**
(a measured rate, no hypothesis) and **synthetic** (true by construction); see
[How to read the results](#how-to-read-the-results). The full table, with n, intervals
and sources, is in [docs/RESULTS.md](docs/RESULTS.md).

| Tool | Data | Result | n | Label |
|---|---|---|---|---|
| receipts | SciArena-Eval votes | **Null.** The response with the higher W1+W2 flag rate (rules v0.1) lost the human vote in 50.09% of votes (95% CI 45.9% to 54.27%), sign-test p = 1.0 | 569 | held-out |
| receipts | Theorizer laws (released export) | T1: 1.36% of cited (law, evidence ID) pairs resolve to no evidence record, all through the export's fallback link | 14343 | descriptive |
| receipts | Theorizer laws | T2: 0.88% of laws have an empty scope and an empty evidence list, all in the parametric accuracy-focused condition | 4187 | descriptive |
| receipts | Theorizer laws | W1 (rules v0.1): 37.78% state a number absent from their cited records; 84.62% in the novelty-focused condition, whose laws are quantitative predictions by design | 1887 | descriptive |
| receipts | SciArena-Eval citations | all but one of 31820 inline citations resolve to a listed passage; W1 1.42% and W2 1.4% of resolved citations (rules v0.1; 1.5% and 1.65% under v0.2) | 31819 | descriptive |
| receipts | Theorizer and SciArena flags, read by hand | precision W1 54% (v0.1) and 56% (v0.2); W2 26% and 32%; differences inside the intervals | 50 per check and version | dev |
| receipts | seeded synthetic workspace | 100% of planted defects found, 0 findings on the clean controls | 17 | synthetic |
| audit | CodeScientist full-50 reruns | H1 (audit rules v0.1) **not supported in the predicted direction**: runs the audit flags agreed more with their reruns (0.4408) than runs it passed (0.3433); stratified permutation p = 0.0845 | 80 | held-out |
| audit | CodeScientist external ratings | H2 **null**: soundness 0.6296 flagged against 0.6667 passed, p = 0.8561 (same papers as the dev set) | 20 | exploratory |
| audit | CodeScientist v0.2 held-out (the 13 unused full-50 runs) | **not testable**: the v0.2 audit flags 1 of 13 at error severity, below the preregistered minimum of 3 per group | 13 | held-out |
| audit | CodeScientist Table 4 discoveries | v0.1: 9 of 13 rejected discoveries flagged by a code meant for the reviewers' reason; 3 of 6 accepted carry an error-severity code. v0.2: 8 of 13 caught by an intended code; 8 of 13 rejected and 3 of 6 accepted carry an error. Of those 3, 2 are small reporting details a rule-based check can surface (discovery 5's SD 15.8% does not appear in the output; recomputed it is 16.2% sample / 16.0% population. Discovery 3 says "significantly" without a printed test) and 1 is a new R2 error (2 support / 2 refute reruns) | 19 | dev |
| audit | DiscoveryBench synthetic tasks (A5) | Benjamini–Hochberg cuts distractor-column hits from 7.43% to 2.74% of tests (63.14% fewer); with a permuted target, tasks with any hit fall from 73.25% to 3.82%. Derived set (720 queries without a machine-readable relation, 483 scanned): BH cuts distractor hits from 7.42% to 2.79%; combined coverage 70.87% of queries | 4456 / 15356 tests | descriptive / synthetic |
| audit | CodeScientist resistor report | its success-rate table reproduces exactly from its `results.json`, 9 of 9 cells | 9 | descriptive |
| reproduce | CodeScientist reruns as reproductions | numbers recoverable in both runs: 36.92% (v0.1) → 46.15% (v0.2, 95% CI 34.59% to 58.15%); verdicts 4/0/61 (v0.1) → 2 reproduced, 2 not reproduced, 61 inconclusive (v0.2, the expected direction is the source effect's sign; the 2 former "reproduced" pairs contradict their own source run); 27.69% agreement with CodeScientist's own run labels in both | 65 | descriptive |
| reproduce | DiscoveryBench planted effects and nulls, held-out row halves | nulls not reproduced or inconclusive 97.77%; planted effects reproduced 47.77% overall and 96.61% where D1 calls the test decidable | 1569 / 358 / 177 | synthetic |

What these do not show is in [docs/LIMITATIONS.md](docs/LIMITATIONS.md). In short: no
real AutoDiscovery run is public, so the AutoDiscovery adapter is tested on synthetic
fixtures only. The audit's dev set is not blind, its v0.1 held-out prediction failed, and
the v0.2 held-out was not testable. W1 and W2 are lexical (on a hand-checked sample,
about half of W1 flags and a third of W2 flags were real). E6 needs local source text.
Parsing is regex-level. DiscoveryBench's planted and null labels are impure. Samples are
small, and most CodeScientist rerun pairs lack the numbers a verdict needs.

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

`fetch all` fetches every source. If you fetch one source at a time, note that the
reproduction analysis also needs `codescientist-example-experiments`
(`consilience-ai2 fetch codescientist-example-experiments`).

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
