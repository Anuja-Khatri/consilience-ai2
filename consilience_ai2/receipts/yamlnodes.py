"""Read YAML as Pandoc metadata sees it (every scalar a string), keeping line numbers.

Pandoc reads metadata scalars as text, so ``corpus_id: 289622360`` and
``retrieved: 2026-08-29`` arrive as the strings written. ``load_with_lines`` composes the
document with PyYAML's ``BaseLoader`` (no type resolution) and returns plain Python
values (``str``, ``list``, ``dict``) together with a map from key paths to the 1-based
line where each key is written. A repeated key keeps the last value, as PyYAML does.
"""

from __future__ import annotations

from typing import Any

import yaml

Path_ = tuple[str, ...]


class YamlError(ValueError):
    """The text is not valid YAML."""


def _convert(node: yaml.Node, path: Path_, lines: dict[Path_, int]) -> Any:
    if isinstance(node, yaml.ScalarNode):
        return node.value
    if isinstance(node, yaml.SequenceNode):
        return [_convert(n, path + (str(i),), lines) for i, n in enumerate(node.value)]
    if isinstance(node, yaml.MappingNode):
        out: dict[str, Any] = {}
        for k, v in node.value:
            key = k.value if isinstance(k, yaml.ScalarNode) else str(k.value)
            lines[path + (key,)] = k.start_mark.line + 1
            out[key] = _convert(v, path + (key,), lines)
        return out
    return None  # pragma: no cover


def load_with_lines(text: str, first_line: int = 1) -> tuple[Any, dict[Path_, int]]:
    """``(value, lines)`` for one YAML document; ``first_line`` offsets the line numbers
    (for front matter that starts below line 1). Empty text gives ``(None, {})``."""
    try:
        node = yaml.compose(text, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        raise YamlError(str(exc).replace("\n", " ")) from exc
    if node is None:
        return None, {}
    lines: dict[Path_, int] = {}
    value = _convert(node, (), lines)
    if first_line != 1:
        lines = {k: v + first_line - 1 for k, v in lines.items()}
    return value, lines
