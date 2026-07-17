"""T018 — Golden tests du renderer Mermaid de diagrammes de classes."""

from __future__ import annotations

from codeatlas.renderers.mermaid.class_diagram import render_class_diagram

from .corpus import corpus_graph


def test_order_module_class_diagram(assert_golden) -> None:
    diagram = render_class_diagram(corpus_graph(), "main/shopdemo.models.order")
    assert_golden("class_order.mmd", diagram)


def test_product_module_class_diagram_excludes_private_by_default(assert_golden) -> None:
    diagram = render_class_diagram(corpus_graph(), "main/shopdemo.models.product")
    assert "_ProductCache" not in diagram
    assert "_rounded" not in diagram
    assert_golden("class_product.mmd", diagram)


def test_diagram_marks_relations_with_uml_arrows() -> None:
    diagram = render_class_diagram(corpus_graph(), "main/shopdemo.models.product")
    assert "Product <|-- DigitalProduct" in diagram


def test_rendering_is_deterministic() -> None:
    first = render_class_diagram(corpus_graph(), "main/shopdemo.services.catalog")
    second = render_class_diagram(corpus_graph(), "main/shopdemo.services.catalog")
    assert first == second
