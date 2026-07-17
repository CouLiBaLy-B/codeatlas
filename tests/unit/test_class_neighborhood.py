"""T084 — Diagramme de classes focalisé : voisinage à rayon N (FR-010)."""

from __future__ import annotations

from codeatlas import api
from codeatlas.config import Config
from codeatlas.renderers.mermaid.class_diagram import render_class_neighborhood
from tests.golden.corpus import corpus_graph

ORDER = "main/shopdemo.models.order.Order"


class TestNeighborhoodDepth:
    def test_depth_1_includes_direct_relations_only(self) -> None:
        diagram = render_class_neighborhood(corpus_graph(), ORDER, depth=1)
        assert "class Order {" in diagram
        assert "class OrderLine {" in diagram  # composée directement
        assert "class Product {" not in diagram  # à distance 2 (via OrderLine)

    def test_depth_2_reaches_transitive_relations(self) -> None:
        diagram = render_class_neighborhood(corpus_graph(), ORDER, depth=2)
        assert "class Product {" in diagram
        assert "Order *-- OrderLine" in diagram
        assert "OrderLine o-- Product" in diagram

    def test_neighborhood_crosses_module_boundaries(self) -> None:
        # CatalogService (services) agrège InMemoryRepo (storage) : modules différents
        catalog = "main/shopdemo.services.catalog.CatalogService"
        diagram = render_class_neighborhood(corpus_graph(), catalog, depth=1)
        assert "class InMemoryRepo {" in diagram

    def test_deterministic(self) -> None:
        first = render_class_neighborhood(corpus_graph(), ORDER, depth=2)
        assert first == render_class_neighborhood(corpus_graph(), ORDER, depth=2)


class TestApiWiring:
    def test_render_diagram_honors_depth_for_class_focus(self) -> None:
        graph = corpus_graph()
        spec_1 = api.DiagramSpec(type="class", focus="Order", depth=1)
        spec_2 = api.DiagramSpec(type="class", focus="Order", depth=2)
        assert "class Product {" not in api.render_diagram(graph, spec_1, Config())
        assert "class Product {" in api.render_diagram(graph, spec_2, Config())

    def test_module_focus_still_renders_whole_module(self) -> None:
        graph = corpus_graph()
        diagram = api.render_diagram(
            graph, api.DiagramSpec(type="class", focus="models.product"), Config()
        )
        assert "class Product {" in diagram
        assert "class DigitalProduct {" in diagram
