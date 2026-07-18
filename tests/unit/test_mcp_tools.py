"""T010 — Outils MCP comme fonctions pures : exactes, bornées, jamais d'invention."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.bridge import tools
from codeatlas.config import Config
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


class TestSearchSymbol:
    def test_exact_match_with_location_and_doc(self, graph: CodeGraph) -> None:
        result = tools.search_symbol(graph, "price_with_tax")
        ids = {m["id"] for m in result["matches"]}
        assert "main/shopdemo.models.product.Product.price_with_tax" in ids
        first = next(
            m for m in result["matches"]
            if m["id"] == "main/shopdemo.models.product.Product.price_with_tax"
        )
        assert first["file"] == "shopdemo/models/product.py"
        assert "rate" in first["signature"]
        assert first["doc"] == "Prix TTC pour un taux de TVA donné."

    def test_unknown_symbol_returns_empty_never_invents(self, graph: CodeGraph) -> None:
        assert tools.search_symbol(graph, "nexiste_pas_du_tout") == {
            "matches": [],
            "truncated": False,
        }

    def test_results_are_bounded_and_flagged(self, graph: CodeGraph) -> None:
        result = tools.search_symbol(graph, "o", limit=5)  # très large
        assert len(result["matches"]) == 5
        assert result["truncated"] is True


class TestModuleApi:
    def test_module_api_lists_public_surface(self, graph: CodeGraph) -> None:
        result = tools.module_api(graph, "shopdemo.models.product")
        names = {entry["name"] for entry in result["classes"]}
        assert names == {"Product", "DigitalProduct"}
        assert "_ProductCache" not in str(result)

    def test_ambiguous_module_lists_candidates(self, graph: CodeGraph) -> None:
        result = tools.module_api(graph, "models")  # models et models.* possibles
        assert "candidates" in result or "classes" in result

    def test_unknown_module_is_explicit(self, graph: CodeGraph) -> None:
        result = tools.module_api(graph, "nexiste.pas")
        assert result.get("error")
        assert result.get("candidates") == []


class TestCallersCallees:
    def test_callers_with_certainty(self, graph: CodeGraph) -> None:
        result = tools.callers(graph, "CatalogService.price_of")
        by_id = {c["id"]: c for c in result["callers"]}
        refresh = "main/shopdemo.legacy.pricing.refresh_catalog_price"
        assert by_id[refresh]["certainty"] == "inferred"

    def test_callees(self, graph: CodeGraph) -> None:
        result = tools.callees(graph, "OrderService.place")
        ids = {c["id"] for c in result["callees"]}
        assert "main/shopdemo.storage.repo.InMemoryRepo.find" in ids

    def test_ambiguous_symbol_candidates(self, graph: CodeGraph) -> None:
        result = tools.callers(graph, "price_with_tax")  # Product ET DigitalProduct
        assert result.get("error")
        assert len(result.get("candidates", [])) >= 2

    def test_depth_traverses_levels(self, graph: CodeGraph) -> None:
        # contrat bridge.md : callers(symbol, depth) — niveaux distingués
        shallow = tools.callers(graph, "InMemoryRepo.find", depth=1)
        deep = tools.callers(graph, "InMemoryRepo.find", depth=2)
        ids_shallow = {c["id"] for c in shallow["callers"]}
        by_id = {c["id"]: c for c in deep["callers"]}
        main_id = "main/shopdemo.cli.main"
        assert main_id not in ids_shallow
        assert by_id[main_id]["depth"] == 2


class TestOverviewAndDeadCode:
    def test_overview_counts(self, graph: CodeGraph) -> None:
        result = tools.overview(graph, Config())
        assert result["modules"] == 15
        assert any("GET /products" in e["label"] for e in result["entrypoints"])

    def test_dead_code_listed(self, graph: CodeGraph) -> None:
        result = tools.dead_code(graph)
        ids = {c["id"] for c in result["candidates"]}
        assert "main/shopdemo.quality._forgotten_helper" in ids


def test_determinism(graph: CodeGraph) -> None:
    assert tools.search_symbol(graph, "Product") == tools.search_symbol(graph, "Product")
    assert tools.overview(graph, Config()) == tools.overview(graph, Config())
