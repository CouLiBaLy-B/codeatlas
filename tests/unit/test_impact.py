"""T007 — Analyse d'impact : niveaux exacts, points d'entrée atteints, certitude."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.insights.impact import compute_impact
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"

FIND = "main/shopdemo.storage.repo.InMemoryRepo.find"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


class TestLevels:
    def test_direct_callers_at_level_1(self, graph: CodeGraph) -> None:
        report = compute_impact(graph, (FIND,), depth=1)
        level1 = {entry.id for entry in report.levels[0].entries}
        assert "main/shopdemo.services.orders.OrderService.place" in level1
        assert "main/shopdemo.services.catalog.CatalogService.price_of" in level1

    def test_transitive_callers_at_level_2(self, graph: CodeGraph) -> None:
        report = compute_impact(graph, (FIND,), depth=2)
        level2 = {entry.id for entry in report.levels[1].entries}
        assert "main/shopdemo.cli.main" in level2  # main → place → find

    def test_depth_bounds_propagation(self, graph: CodeGraph) -> None:
        report = compute_impact(graph, (FIND,), depth=1)
        assert len(report.levels) == 1

    def test_uncertain_links_flagged(self, graph: CodeGraph) -> None:
        price_of = "main/shopdemo.services.catalog.CatalogService.price_of"
        report = compute_impact(graph, (price_of,), depth=1)
        by_id = {entry.id: entry for entry in report.levels[0].entries}
        # refresh_catalog_price appelle price_of via getattr → lien incertain
        refresh = "main/shopdemo.legacy.pricing.refresh_catalog_price"
        assert by_id[refresh].certainty == "inferred"

    def test_entrypoints_reached_marked(self, graph: CodeGraph) -> None:
        report = compute_impact(graph, (FIND,), depth=3)
        assert "main/shopdemo.cli.main" in report.entrypoints_reached
        assert "main/shopdemo.webapp.create_product" in report.entrypoints_reached

    def test_unreferenced_symbol_is_explicitly_empty(self, graph: CodeGraph) -> None:
        dead = "main/shopdemo.quality.forgotten_public_api"
        report = compute_impact(graph, (dead,), depth=3)
        assert report.levels == ()
        assert report.entrypoints_reached == ()


class TestFileTarget:
    def test_file_impact_covers_all_its_symbols(self, graph: CodeGraph) -> None:
        targets = tuple(
            n.id for n in graph.nodes_in_file("shopdemo/storage/repo.py")
        )
        report = compute_impact(graph, targets, depth=1)
        level1 = {entry.id for entry in report.levels[0].entries}
        # les importeurs du module ET les appelants des méthodes
        assert "main/shopdemo.services.catalog" in level1  # import
        assert "main/shopdemo.services.orders.OrderService.place" in level1  # appel


def test_determinism(graph: CodeGraph) -> None:
    assert compute_impact(graph, (FIND,), depth=3) == compute_impact(graph, (FIND,), depth=3)
