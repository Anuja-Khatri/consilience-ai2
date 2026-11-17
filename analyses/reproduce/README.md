# Analyses for the reproduction verdict (C3)

```bash
consilience-ai2 fetch codescientist
consilience-ai2 fetch codescientist-full50
consilience-ai2 fetch discoverybench
python analyses/reproduce/run.py        # writes results/reproduce.json
```

- `codescientist_reruns.py`: (a) CodeScientist reruns read as reproductions
  (`descriptive`). The run's first completed copy is the source, every later completed
  copy a reproduction; the records are built from each run's final `results.json`.
- `discoverybench_planted.py`: (b) DiscoveryBench synthetic tasks, planted effects and
  nulls reproduced on held-out row halves (`synthetic`).
- `run.py`: runs both and writes the results file. Each module also prints its summary
  when run on its own.

The design of each analysis is in its module docstring; the results and their limits
are in [docs/reproduce.md](../../docs/reproduce.md). (c), the P1 commit-order tests on a
scratch git repository, is `tests/reproduce/test_commit_order.py`.
