# Contributing

House rules (from [docs/SPEC.md](docs/SPEC.md), "Design principles"): deterministic, no
model calls; every finding carries a receipt; three outcomes (`pass`, `flag`,
`refuse`/`UNCHECKABLE`) and never a guess; no Ai2 data in the repository; every reported
number renders from `results/registry.json`.

Run `make ci` before every commit. It must be green.

## The worker contract

The three tools are built as separate components (`receipts`, `audit`, `reproduce`) on
separate branches, then merged. A component touches **only its own files**, so branches
merge without conflicts.

### Where a component's files go

For component `<c>` in `receipts`, `audit`, `reproduce`:

| What | Where |
|---|---|
| Code | `consilience_ai2/<c>/` (create `__init__.py`; the API lives here) |
| CLI | `consilience_ai2/<c>/cli.py` exposing `register(subparsers)` (below) |
| Packaged fixtures the code needs at run time | `consilience_ai2/<c>/data/` (shipped in the wheel) |
| Tests | `tests/<c>/test_*.py`, fixtures in `tests/<c>/conftest.py` (pytest runs with `--import-mode=importlib`, so file names never clash; no network) |
| User-facing examples (synthetic only) | `examples/<c>/` |
| Analyses on fetched Ai2 data | `analyses/<c>/` (scripts plus an optional `README.md`) |
| Preregistrations | `prereg/<c>/` (committed in a commit **before** the scoring commit) |
| Results | `results/<c>.json`, written only with `write_results("<c>", ...)` |
| Component doc | `docs/<c>.md` (scanned by the numbers lock) |
| Numbers allow-list | `scripts/numbers_allowlist/<c>.txt` (structural constants only) |
| Claude Code plugin | `plugins/consilience-<c>/` with `marketplace-entry.json` and `skills/<skill>/SKILL.md` |

### Shared files a component must NOT edit

The integrator owns these; a component branch leaves them untouched:

- `consilience_ai2/core/**`, `consilience_ai2/cli.py`, `consilience_ai2/__init__.py`,
  `consilience_ai2/__main__.py`, `consilience_ai2/fetch/**` (including `sources.yaml`);
- `pyproject.toml`, `Makefile`, `MANIFEST.in`, `.github/**`, `.gitignore`;
- `README.md`, `NOTICE`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/SPEC.md`,
  and the integrator's docs (`docs/RESULTS.md`, `docs/LIMITATIONS.md`,
  `docs/INTEGRATION.md`);
- the generated files: `results/registry.json`, `results/NUMBERS_LOCK.json`,
  `docs/tables/results.md`, `.claude-plugin/marketplace.json`;
- `scripts/*.py`, `scripts/numbers_allowlist/core.txt`, `scripts/secrets_allowlist.txt`;
- `tests/conftest.py` and the core tests (`tests/test_*.py` that are not `test_<c>_*`).

If a component needs something in core (a helper, a new dependency, a new source in
`sources.yaml`), it says so in its hand-off; it does not edit the shared file. Missing
helpers can live in the component until the integrator promotes them.

### How a CLI registers

Core discovers components; nothing is listed by hand. For each name in
`consilience_ai2.core.registry.COMPONENTS` (`receipts`, `audit`, `reproduce`, `fetch`),
`consilience-ai2` imports `consilience_ai2.<name>.cli` if it exists and calls its
`register`:

```python
# consilience_ai2/receipts/cli.py
def register(subparsers) -> None:
    p = subparsers.add_parser("receipts", help="...", description="...")
    p.add_argument("workspace")
    p.add_argument("--json", metavar="PATH")
    p.set_defaults(func=run)

def run(args) -> int:          # the process exit code
    ...
```

Exit codes: `0` pass, `1` findings that fail the run (or a failed input), `2` usage
error. A missing component is skipped; a component that exists but fails to import is a
bug and raises.

### How a component reports findings

Use `consilience_ai2.core.findings`:

```python
from consilience_ai2.core.findings import Finding, InputRecord, Receipt, Report
from consilience_ai2.core.hashing import sha256_file, sha256_text
from consilience_ai2.core.normalise import NORMALISATION_VERSION, find_normalised
from consilience_ai2.core.numbers import extract_numbers, agrees_at_printed_precision

report = Report(tool="consilience-ai2 receipts", tool_version=__version__,
                inputs=[InputRecord.from_file(p, role="evidence", relative_to=ws)],
                extra={"checked_spans": n})
report.add(Finding("E6", "info", "FOUND", file="index.qmd", line=12, key="k",
                   receipt=Receipt("paperstore:123", sha, offset=s, end=e,
                                   normalisation=NORMALISATION_VERSION)))
report.write(out_path)                 # deterministic JSON
print("\n".join(report.annotations()))  # ::error file=…,line=…::E1 …
return report.exit_code()
```

- Codes are uppercase (`E1`, `W2`, `T1`, `A5`, `R4`, `F1`, `D1`, `V1`, `P1`).
- Severity is `error`, `warning` or `info`. Passing checks emit an `info` finding with a
  receipt.
- `details` carries component fields (q values, spans, verdicts); it must be JSON.
- Never pass a timestamp unless the user asks for one (`Report.created`).
- Text comparisons use `core.normalise` (record `NORMALISATION_VERSION`); numbers use
  `core.numbers` (an `ambiguous` token is uncheckable, not a mismatch).

### How a component emits results

```python
from consilience_ai2.core.results import metric, write_results

write_results("audit", [
    metric("audit.bh_fdr_reduction", 0.62, n=903, ci_lo=0.55, ci_hi=0.68,
           source="fetch:discoverybench", dev_or_heldout="descriptive",
           caveats=["synthetic tasks only"], test="permutation, 10000 draws, seed 0"),
])
```

- `metric_id` starts with `<c>.`; `dev_or_heldout` is one of `dev`, `heldout`,
  `exploratory`, `descriptive`, `synthetic`.
- Analyses read data with `consilience_ai2.fetch.require("<source>")` (no network; it
  says which `fetch` command to run). Fixed seeds; same data, same bytes.
- Do not commit `results/registry.json` or the lock: the integrator runs `make lock`.
  On a component branch, `make ci` warns that the registry is stale; that is expected.
- Numbers in `docs/<c>.md` and `analyses/**/*.md` must render from your results file or
  be allow-listed in `scripts/numbers_allowlist/<c>.txt` (thresholds, margins).

### Plugins

`plugins/consilience-<c>/marketplace-entry.json`:

```json
{"name": "consilience-<c>", "description": "...", "keywords": ["..."]}
```

plus `plugins/consilience-<c>/skills/<skill>/SKILL.md` with frontmatter `name` (equal to
the directory name), `description` and `allowed-tools`, in the asta-plugins format. No
`plugin.json`. The integrator runs `make marketplace` to list it.

### Preregistration

A held-out test is preregistered by committing `prereg/<c>/<name>.md` (hypothesis, data,
test, threshold, frozen rule version) in its own commit, before the commit that adds the
scoring code's output. Record that commit hash in the metric's `prereg` field.

## Data

Never commit downloaded data, keys or secrets. `make secrets` fails on key-shaped
strings, archives, files over 2 MB and model identifiers. The fetch cache refuses any
location inside the repository.
