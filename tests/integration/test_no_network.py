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


def test_site_loads_no_external_resource(
    tmp_path: Path, corpus: Path, runner: CliRunner
) -> None:
    """T029/FR-019 : aucune ressource chargée depuis l'extérieur (scripts, styles, images).

    Les simples liens de navigation `<a href>` sortants sont tolérés (crédit du
    thème) : ils ne chargent rien à la consultation.
    """
    out = tmp_path / "docs"
    result = runner.invoke(main, ["build", str(corpus), "--out", str(out)])
    assert result.exit_code == 0, result.output
    for page in sorted((out / "site").rglob("*.html")):
        text = page.read_text(encoding="utf-8", errors="replace")
        assert 'src="http' not in text, page.name
        assert "src='http" not in text, page.name
        for chunk in text.split("<link")[1:]:
            head = chunk.split(">", 1)[0]
            assert 'href="http' not in head, (page.name, head)
    for sheet in sorted((out / "site").rglob("*.css")):
        text = sheet.read_text(encoding="utf-8", errors="replace")
        assert "url(http" not in text and "@import url('http" not in text, sheet.name


def test_workshop_session_rebuild_with_network_blocked(
    tmp_path: Path, corpus: Path, no_network: None
) -> None:
    """T029/FR-012 : le cycle du mode atelier n'émet aucun octet vers l'extérieur."""
    import shutil
    from dataclasses import replace

    from codeatlas.config import SiteCfg, load_config
    from codeatlas.serve.session import WorkshopSession

    repo = tmp_path / "repo"
    shutil.copytree(corpus, repo)
    config = replace(load_config(repo), site=SiteCfg(enabled=False))
    session = WorkshopSession(repo, config, workdir=tmp_path / "atelier")
    assert session.build() is True
    target = repo / "shopdemo" / "quality.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n\ndef offline() -> None:\n    pass\n",
        encoding="utf-8",
    )
    session.notify_change("shopdemo/quality.py")
    assert session.flush() is True
    assert session.build_token == 2


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
