"""T046 — Scénarios d'acceptation US3 : page « Santé du code » dans le site."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    corpus = Path(__file__).parents[2] / "examples" / "python-demo"
    out = tmp_path_factory.mktemp("atlas-us3") / "out"
    result = CliRunner().invoke(main, ["build", str(corpus), "--out", str(out)])
    assert result.exit_code == 0, result.output
    return out


@pytest.fixture(scope="module")
def health_page(built: Path) -> str:
    return (built / "docs" / "health.md").read_text(encoding="utf-8")


class TestScenario1PageSante:
    def test_per_module_metrics_table(self, health_page: str) -> None:
        assert "shopdemo.quality" in health_page
        assert "shopdemo.models.order" in health_page

    def test_visual_statuses_present(self, health_page: str) -> None:
        assert "🔴" in health_page  # critique (tangled_pricing)
        assert "✅" in health_page  # sain

    def test_worst_functions_listed(self, health_page: str) -> None:
        assert "tangled_pricing" in health_page

    def test_health_in_navigation(self, built: Path) -> None:
        assert "health.md" in (built / "mkdocs.yml").read_text(encoding="utf-8")


class TestScenario2CodeMort:
    def test_dead_code_section_with_confidence(self, health_page: str) -> None:
        assert "_forgotten_helper" in health_page
        assert "forgotten_public_api" in health_page

    def test_live_symbols_not_in_dead_section(self, health_page: str) -> None:
        assert "OrderService.place" not in health_page
