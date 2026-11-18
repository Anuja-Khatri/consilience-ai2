# C2 analyses

`python analyses/audit/run_all.py` (after `consilience-ai2 fetch codescientist
codescientist-example-experiments codescientist-full50 discoverybench`) writes
`results/audit.json`, `dev_table.md` and `details/*.json`. No network, no model calls,
fixed seeds; reruns are byte-identical.

| Script | What | Split |
|---|---|---|
| `rules_versions.py` | runs an analysis under a frozen rule version taken from git (v0.1 = tree `cca16a0`) | - |
| `codescientist_dev.py` | the 19 CodeScientist Table 4 verdicts, rules v0.1 (frozen) and v0.2 side by side | dev |
| `resistor_table.py` | the resistor report's table recomputed from results.json | descriptive |
| `discoverybench_a5.py` | A5: distractor hits with and without BH on synthetic tasks; machine-readable and derived gold sets | descriptive / synthetic |
| `codescientist_heldout.py` | rules v0.1 preregistered held-out tests (`prereg/audit/heldout_prereg.md`), always run with the frozen v0.1 rules | heldout / exploratory |

See docs/audit.md for the results and their limits.
