# consilience-ai2

Deterministic validity checks for agent-produced science, read from the native file
formats of the Allen Institute for AI's Asta tools.

**Independent work, not affiliated with or endorsed by the Allen Institute for AI (Ai2).**

> Status: skeleton (0.1.0). The core (receipts, normalisation, number extraction,
> findings schema, results registry) and `consilience-ai2 fetch` are in place. The three
> tools below are being built; this README will say what each one measured, with every
> number rendered from `results/registry.json`.

## What it is

Science agents write reports with evidence, run experiments and reproduce findings.
This package checks those outputs with rule-based code: no model calls, and the same
input gives byte-identical output. Every finding carries a **receipt**: the SHA-256 of
the source it checked and the location (file and line, or character offsets). Passing
checks emit receipts too. Input that cannot be decided is reported as such, never
skipped.

Three tools are coming:

| Command | Checks | Reads |
|---|---|---|
| `consilience-ai2 receipts` | Is every quote real, resolvable and verbatim, and does the claim overstate it (in number or in certainty)? | Asta workspace `evidence.yml`, `references.bib`, `.qmd` `.ev` spans; Theorizer exports; SciArena citations |
| `consilience-ai2 audit` | Do the reported numbers come from the run? Is the n right? Is there a real test, a real baseline, and control for many tests? | AutoDiscovery `mcts_node_*.json`; CodeScientist experiment directories; DiscoveryBench tasks |
| `consilience-ai2 reproduce` | Is the reproduction the same quantity, can it be decided at all, and what do the numbers say against thresholds committed in advance? | A reproduction record (YAML/JSON) |

The design and every check code are in [docs/SPEC.md](docs/SPEC.md).

## Install

```bash
pip install "git+https://github.com/Anuja-Khatri/consilience-ai2"
# optional: unit-aware comparability for `reproduce`
pip install "consilience-ai2[consilience] @ git+https://github.com/Anuja-Khatri/consilience-ai2"
```

Python 3.11 or newer. Runtime dependencies: PyYAML, numpy, scipy.

## Data

The results are measured on data released by Ai2 and collaborators. Nothing is
redistributed here; fetch it yourself, pinned and verified:

```bash
consilience-ai2 fetch --list          # sources, pins and cache status
consilience-ai2 fetch all             # into ~/.cache/consilience-ai2 (or $CONSILIENCE_AI2_DATA)
```

Each file is checked against its SHA-256 and each git repository against its commit; a
mismatch is refused. Sources, licences and citations: `consilience_ai2/fetch/sources.yaml`
and [NOTICE](NOTICE).

## Development

```bash
make setup     # .venv with the package in editable mode and the dev tools
make ci        # ruff, pytest (no network), numbers lock, marketplace check, secret scan
```

Contributor rules, including the contract for component code: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT (see [LICENSE](LICENSE)). Credits for every third-party artefact: [NOTICE](NOTICE).
