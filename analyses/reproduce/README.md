# Analyses for the reproduction verdict (C3)

```bash
consilience-ai2 fetch codescientist
consilience-ai2 fetch codescientist-full50
consilience-ai2 fetch codescientist-example-experiments   # searched for the second batch
consilience-ai2 fetch discoverybench
python analyses/reproduce/run.py        # writes results/reproduce.json
```

- `codescientist_reruns.py`: (a) CodeScientist reruns read as reproductions
  (`descriptive`). The run's first completed copy is the source, every later completed
  copy a reproduction. v0.1 builds the records from each run's final `results.json`;
  v0.2 also reads its `to_save/` files and `log.json`, and chooses among several
  comparisons by the hypothesis and the experiment plan. Both are computed on the same
  pairs and written side by side. It also searches for run outputs of the batch without
  expert notes.
- `cs_extract.py`: the v0.2 parsers and rules (tolerant JSON, bootstrap blocks in results,
  `to_save/` and log files, the primary-comparison rule, the classification of runs
  without a bootstrap block). Pure functions; tested in `tests/reproduce/test_cs_extract.py`.
- `discoverybench_planted.py`: (b) DiscoveryBench synthetic tasks, planted effects and
  nulls reproduced on held-out row halves (`synthetic`), with the v0.2 sensitivity
  analysis (Spearman verdicts; Pearson, Spearman and binned mutual-information detection)
  and the derived planted pairs from prose gold hypotheses.
- `run.py`: runs both and writes the results file. Each module also prints its summary
  when run on its own.

The v0.2 extraction rules are preregistered in `prereg/reproduce/cs_extraction_v0_2.md`,
with three corrections made before any number was committed in
`prereg/reproduce/cs_extraction_v0_2_deviations.md`. Every v0.2 verdict uses verdict rule
v0.2 (the expected direction is the source's sign; deviation 4 in the same file, decided
after the extraction results were seen); the v0.1 numbers keep verdict rule v0.1, and the
v0.2 extraction is also judged with rule v0.1 to separate the two changes. The design of each analysis is in its
module docstring; the results and their limits are in
[docs/reproduce.md](../../docs/reproduce.md). (c), the P1 commit-order tests on a scratch
git repository, is `tests/reproduce/test_commit_order.py`; the demo of the workflow P1
credits is `examples/reproduce/demo_commit_order.py`.
