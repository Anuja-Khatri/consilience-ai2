# SYNTHETIC AutoDiscovery fixtures

**Everything in this directory is synthetic.** No real AutoDiscovery run outputs are
public, and none are used here. `make_fixtures.py` writes these files from the released
schema of allenai/asta-autodiscovery (commit 30e080f): the keys of `MCTSNode.to_dict`,
`BeliefTrueFalse.DistributionFormat.to_dict`, `ExperimentPlan` and the hosted
`ExperimentModel`. The survey dataset, the nodes, their code, output, analysis and reviews
are invented.

- `synthetic_run/`: a local `--out_dir` (`args.json`, `dataset_metadata.json`, the root
  `mcts_node_1_0.json`, experiment nodes `mcts_node_2_0.json` to `mcts_node_2_11.json`,
  `mcts_nodes_all.json`).
- `synthetic_hosted/results.json`: the same first nine nodes as a hosted export.
- `planted.json`: the audit codes planted in each node (none in `node_2_0`).

| node | planted |
|---|---|
| node_2_0 | nothing (clean) |
| node_2_1 | A1: the analysis reports a number the output never printed |
| node_2_2 | A2 (and R3): the plan says 2000 respondents, the code samples 20 |
| node_2_3 | A3: the code reads a column that is not in the metadata |
| node_2_4 | A4: "significantly" with no test printed |
| node_2_5 | A5: one of six subgroup p values claimed, not significant after BH |
| node_2_6 | A6: a surprising null at n = 30 |
| node_2_7 | A7: an effect with a t statistic but no effect size |
| node_2_8 | R1: the only comparator is chance |
| node_2_9 | R4: the reported AUC is a literal in the code |
| node_2_10 | R5: interaction features are built and never used |
| node_2_11 | U1: no output at all |

```bash
consilience-ai2 audit run examples/audit/autodiscovery/synthetic_run --json /tmp/va.json
```
