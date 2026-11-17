# Plugins

Claude Code plugins, in the marketplace layout of
[allenai/asta-plugins](https://github.com/allenai/asta-plugins) (read at commit a2dcade):

- one marketplace file at the repository root: `.claude-plugin/marketplace.json`;
- each plugin in `plugins/<plugin-name>/`, with its skills in
  `plugins/<plugin-name>/skills/<skill-name>/SKILL.md` (YAML frontmatter with `name`,
  `description` and `allowed-tools`) and any scripts beside the skill;
- no per-plugin `plugin.json`: the marketplace is the single metadata source.

No plugins are listed yet. Each component adds its own plugin directory with a
`marketplace-entry.json` (name, description, keywords); `make marketplace` regenerates
the marketplace file from those entries. See `scripts/build_marketplace.py`.

## Installing (once plugins are listed)

```bash
claude plugin marketplace add Anuja-Khatri/consilience-ai2
claude plugin install <plugin-name>
```
