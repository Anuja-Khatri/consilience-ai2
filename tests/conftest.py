"""Shared fixtures. No test touches the network."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo_root() -> Path:
    return REPO


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Fail any test that tries to open a network connection."""

    def guard(*args, **kwargs):
        raise RuntimeError("tests must not use the network")

    monkeypatch.setattr(socket, "create_connection", guard)
    monkeypatch.setattr(socket.socket, "connect", guard)
