"""T020 — Golden tests des pages de référence API générées depuis l'IR."""

from __future__ import annotations

from codeatlas.config import Config
from codeatlas.site.pages import render_module_page

from .corpus import corpus_graph


def test_product_module_page(assert_golden) -> None:
    page = render_module_page(corpus_graph(), "main/shopdemo.models.product", Config())
    assert_golden("page_product.md", page)


def test_module_page_contains_signatures_and_docs() -> None:
    page = render_module_page(corpus_graph(), "main/shopdemo.models.product", Config())
    assert "price_with_tax" in page
    assert "rate: float = 0.2" in page
    assert "Un produit physique du catalogue." in page


def test_module_page_hides_private_symbols_by_default() -> None:
    page = render_module_page(corpus_graph(), "main/shopdemo.models.product", Config())
    assert "_ProductCache" not in page


def test_page_ends_with_single_newline() -> None:
    page = render_module_page(corpus_graph(), "main/shopdemo.models.order", Config())
    assert page.endswith("\n")
    assert not page.endswith("\n\n\n")
