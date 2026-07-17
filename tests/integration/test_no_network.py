"""T023 — SC-007 : la génération complète ne déclenche AUCUN appel réseau."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main


@pytest.fixture()
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("appel réseau détecté pendant la génération (SC-007)")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)


def test_full_build_with_network_blocked(
    tmp_path: Path, corpus: Path, runner: CliRunner, no_network: None
) -> None:
    out = tmp_path / "offline"
    result = runner.invoke(main, ["build", str(corpus), "--out", str(out)], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert (out / "site" / "index.html").is_file()
