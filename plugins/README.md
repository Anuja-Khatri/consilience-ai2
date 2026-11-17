# Plugins

Claude Code plugins, in the marketplace layout of
[allenai/asta-plugins](https://github.com/allenai/asta-plugins) (read at commit a2dcade):

- one marketplace file at the repository root: `.claude-plugin/marketplace.json`;
- each plugin in `plugins/<plugin-name>/`, with its skills in
  `plugins/<plugin-name>/skills/<skill-name>/SKILL.md` (YAML frontmatter with `name`,
  `description` and `allowed-tools`) and any scripts or assets beside the skill;
- no per-plugin `plugin.json`: the marketplace is the single metadata source.

| Plugin | Skill | What it runs |
|---|---|---|
| `consilience-receipts` | `evidence-receipts` | `consilience-ai2 receipts check` on an Asta workspace; ships `assets/evidence-receipts.mk` for `make check` |
| `consilience-audit` | `experiment-audit` | `consilience-ai2 audit run` on an AutoDiscovery run or a CodeScientist experiment |
| `consilience-reproduce` | `reproduction-verdict` | `consilience-ai2 reproduce check` on a reproduction record |

Each plugin declares its marketplace entry in `marketplace-entry.json` (name,
description, keywords); `make marketplace` regenerates the marketplace file from those
entries (`scripts/build_marketplace.py`).

## Installing

In Claude Code:

```text
/plugin marketplace add Anuja-Khatri/consilience-ai2
/plugin install consilience-receipts@consilience-ai2
/plugin install consilience-audit@consilience-ai2
/plugin install consilience-reproduce@consilience-ai2
```

From a shell: `claude plugin marketplace add Anuja-Khatri/consilience-ai2`, then
`claude plugin install <plugin>@consilience-ai2`. The skills call the `consilience-ai2`
command: `pip install "git+https://github.com/Anuja-Khatri/consilience-ai2"`.
