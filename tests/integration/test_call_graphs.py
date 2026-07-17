"""T037 — Scénarios d'acceptation US2 : page points d'entrée + commande diagram."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main


@pytest.fixture(scope="module")
def entrypoints_page(tmp_path_factory: pytest.TempPathFactory) -> str:
    corpus = Path(__file__).parents[2] / "examples" / "python-demo"
    out = tmp_path_factory.mktemp("atlas-us2") / "out"
    result = CliRunner().invoke(main, ["build", str(corpus), "--out", str(out)])
    assert result.exit_code == 0, result.output
    return (out / "docs" / "entrypoints.md").read_text(encoding="utf-8")


class TestScenario1PageEntrypoints:
    def test_all_entrypoints_listed(self, entrypoints_page: str) -> None:
        assert "GET /products" in entrypoints_page
        assert "POST /products" in entrypoints_page
        assert "shopdemo.cli.main" in entrypoints_page

    def test_flow_diagrams_embedded(self, entrypoints_page: str) -> None:
        assert "flowchart" in entrypoints_page

    def test_legend_explains_uncertain_links(self, entrypoints_page: str) -> None:
        # légende : trait plein = sûr, pointillé = incertain
        assert "pointillé" in entrypoints_page or "dotted" in entrypoints_page


class TestScenario2DiagrammeFocalise:
    def test_calls_diagram_to_stdout(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["diagram", str(corpus), "--type", "calls", "--focus", "cli.main", "--depth", "2"],
        )
        assert result.exit_code == 0, result.output
        assert "flowchart" in result.output
        assert "tangled_pricing" in result.output

    def test_depth_bounds_the_diagram(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["diagram", str(corpus), "--type", "calls", "--focus", "cli.main", "--depth", "1"],
        )
        assert result.exit_code == 0
        assert "InMemoryRepo.find" not in result.output

    def test_deps_diagram_supported(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["diagram", str(corpus), "--type", "deps"])
        assert result.exit_code == 0
        assert "graph LR" in result.output

    def test_class_diagram_focused_on_module(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["diagram", str(corpus), "--type", "class", "--focus", "models.order"]
        )
        assert result.exit_code == 0
        assert "classDiagram" in result.output
        assert "OrderLine" in result.output

    def test_ambiguous_focus_is_usage_error(self, corpus: Path, runner: CliRunner) -> None:
        # price_with_tax existe sur Product ET DigitalProduct
        result = runner.invoke(
            main, ["diagram", str(corpus), "--type", "calls", "--focus", "price_with_tax"]
        )
        assert result.exit_code == 2
        assert "ambigu" in result.output

    def test_unknown_focus_is_usage_error(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["diagram", str(corpus), "--type", "calls", "--focus", "nexiste.pas"]
        )
        assert result.exit_code == 2


class TestScenario3LiensIncertains:
    def test_inferred_edges_rendered_dotted(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            ["diagram", str(corpus), "--type", "calls", "--focus", "refresh_catalog_price"],
        )
        assert result.exit_code == 0, result.output
        assert "-.->" in result.output  # appel dynamique getattr → pointillés
        assert "price_of" in result.output
