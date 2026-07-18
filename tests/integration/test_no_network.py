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


def test_export_and_impact_with_network_blocked(
    corpus: Path, runner: CliRunner, no_network: None
) -> None:
    """FR-005 (feature 003) : le pont IA n'émet aucun octet vers l'extérieur."""
    result = runner.invoke(main, ["export", str(corpus)], catch_exceptions=False)
    assert result.exit_code == 0
    result = runner.invoke(
        main,
        ["impact", str(corpus), "--focus", "InMemoryRepo.find"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_mcp_tools_with_network_blocked(corpus: Path, no_network: None) -> None:
    """SC-003 (feature 003) : chaque outil du serveur répond sans réseau."""
    from codeatlas import api
    from codeatlas.bridge import tools
    from codeatlas.config import Config

    graph = api.analyze(corpus)
    assert tools.overview(graph, Config())["modules"] == 15
    assert tools.search_symbol(graph, "Product")["matches"]
    assert tools.module_api(graph, "shopdemo.models.product")["classes"]
    assert tools.callers(graph, "CatalogService.price_of")["callers"]
    assert tools.impact(graph, "InMemoryRepo.find", depth=2)["levels"]
    assert tools.dead_code(graph)["candidates"]
