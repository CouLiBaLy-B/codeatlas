"""T060 — Scénarios d'acceptation US5 : vue architecture dans le site."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main

LAYERED = Path(__file__).parents[2] / "examples" / "layered-demo"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("atlas-us5") / "out"
    result = CliRunner().invoke(main, ["build", str(LAYERED), "--out", str(out)])
    assert result.exit_code == 0, result.output
    return out


@pytest.fixture(scope="module")
def architecture_page(built: Path) -> str:
    return (built / "docs" / "architecture.md").read_text(encoding="utf-8")


class TestScenario1CouchesDetectees:
    def test_layers_presented_with_diagram(self, architecture_page: str) -> None:
        assert "api" in architecture_page
        assert "domain" in architecture_page
        assert "infra" in architecture_page
        assert "flowchart" in architecture_page or "graph" in architecture_page

    def test_page_in_navigation(self, built: Path) -> None:
        assert "architecture.md" in (built / "mkdocs.yml").read_text(encoding="utf-8")


class TestScenario2ViolationSignalee:
    def test_violation_listed_with_involved_packages(self, architecture_page: str) -> None:
        assert "webshop.infra" in architecture_page
        assert "webshop.api" in architecture_page
        assert "legacy_bridge" in architecture_page  # l'indice traçable


class TestScenario3PatternsSurPagesClasses:
    def test_singleton_mentioned_on_class_page(self, built: Path) -> None:
        page = (built / "docs" / "modules" / "webshop.infra.database.md").read_text(
            encoding="utf-8"
        )
        assert "singleton" in page.lower()

    def test_patterns_listed_on_architecture_page(self, architecture_page: str) -> None:
        for pattern in ("singleton", "factory", "observer", "adapter", "decorator"):
            assert pattern in architecture_page.lower()
