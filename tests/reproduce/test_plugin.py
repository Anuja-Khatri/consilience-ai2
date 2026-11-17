"""The plugin is in the asta-plugins layout: entry file, one skill, frontmatter."""

from __future__ import annotations

import json

import yaml


def test_plugin_layout(repo_root):
    root = repo_root / "plugins" / "consilience-reproduce"
    entry = json.loads((root / "marketplace-entry.json").read_text())
    assert entry["name"] == "consilience-reproduce"
    assert set(entry) <= {"name", "description", "keywords", "dependencies", "strict"}
    assert not (root / "plugin.json").exists()
    skills = sorted(p for p in (root / "skills").iterdir() if p.is_dir())
    assert [p.name for p in skills] == ["reproduction-verdict"]
    text = (skills[0] / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front = yaml.safe_load(text.split("---\n")[1])
    assert set(front) == {"name", "description", "allowed-tools"}
    assert front["name"] == skills[0].name
    assert "consilience-ai2 reproduce" in front["allowed-tools"]


def test_skill_quotes_the_rubric_wording(repo_root):
    text = (repo_root / "plugins" / "consilience-reproduce" / "skills" /
            "reproduction-verdict" / "SKILL.md").read_text(encoding="utf-8")
    text = " ".join(text.split())
    for phrase in ("A proxy is a caveat carried with the verdict, never a verdict.",
                   "A substitution is not a reproduction and is not run.",
                   "Read the verdict from the numbers, not from the prose."):
        assert phrase in text
