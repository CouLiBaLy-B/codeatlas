"""T068 — Tests contrat de l'analyseur Java (mêmes exigences que T017)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas.analyzers.base import AnalyzerOptions, IRFragment, discover_files
from codeatlas.analyzers.java.analyzer import JavaAnalyzer
from codeatlas.config import DEFAULT_EXCLUDES
from codeatlas.ir.model import EdgeKind, NodeKind, SubProject, Visibility

CORPUS = Path(__file__).parents[2] / "examples" / "java-demo"
SUB = SubProject(id="main", language="java", root=".")


@pytest.fixture(scope="module")
def fragment() -> IRFragment:
    analyzer = JavaAnalyzer()
    files, unreadable = discover_files(CORPUS, DEFAULT_EXCLUDES, analyzer.extensions)
    assert not unreadable
    return analyzer.analyze(files, SUB, AnalyzerOptions())


class TestNodes:
    def test_modules_named_from_declared_package(self, fragment: IRFragment) -> None:
        module_ids = {n.id for n in fragment.nodes if n.kind is NodeKind.MODULE}
        assert "main/com.shop.Product" in module_ids
        assert "main/com.shop.CatalogService" in module_ids
        assert "main/com.shop.Broken" not in module_ids

    def test_classes_and_interface(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        assert by_id["main/com.shop.Product.Product"].kind is NodeKind.CLASS
        assert by_id["main/com.shop.Catalog.Catalog"].kind is NodeKind.INTERFACE

    def test_javadoc_extracted(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        doc = by_id["main/com.shop.Product.Product"].doc
        assert doc is not None
        assert doc.summary == "Un produit physique du catalogue."
        assert doc.format.value == "javadoc"

    def test_fields_and_methods_with_visibility(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        assert by_id["main/com.shop.Product.Product.name"].kind is NodeKind.ATTRIBUTE
        assert by_id["main/com.shop.Product.Product.name"].visibility is Visibility.PRIVATE
        method = by_id["main/com.shop.Product.Product.priceWithTax"]
        assert method.visibility is Visibility.PUBLIC
        assert "rate" in method.signature
        assert method.complexity is not None

    def test_static_main_flagged(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        main = by_id["main/com.shop.Application.Application.main"]
        assert "static" in main.modifiers

    def test_spring_annotations_recorded_as_decorators(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        method = by_id["main/com.shop.ShopController.ShopController.listProducts"]
        assert any("GetMapping" in m for m in method.modifiers)


class TestEdges:
    def test_extends_and_implements(self, fragment: IRFragment) -> None:
        inherits = {
            (e.source, e.target) for e in fragment.edges if e.kind is EdgeKind.INHERITS
        }
        implements = {
            (e.source, e.target) for e in fragment.edges if e.kind is EdgeKind.IMPLEMENTS
        }
        assert (
            "main/com.shop.DigitalProduct.DigitalProduct",
            "main/com.shop.Product.Product",
        ) in inherits
        assert (
            "main/com.shop.CatalogService.CatalogService",
            "main/com.shop.Catalog.Catalog",
        ) in implements

    def test_same_package_import_edges(self, fragment: IRFragment) -> None:
        imports = {
            (e.source, e.target) for e in fragment.edges if e.kind is EdgeKind.IMPORTS
        }
        assert ("main/com.shop.CatalogService", "main/com.shop.Product") in imports


class TestTolerance:
    def test_invalid_file_skipped(self, fragment: IRFragment) -> None:
        assert len(fragment.skipped) == 1
        assert fragment.skipped[0].path == "src/main/java/com/shop/Broken.java"


def test_determinism() -> None:
    analyzer = JavaAnalyzer()
    files, _ = discover_files(CORPUS, DEFAULT_EXCLUDES, analyzer.extensions)
    first = analyzer.analyze(files, SUB, AnalyzerOptions())
    second = analyzer.analyze(files, SUB, AnalyzerOptions())
    assert [n.id for n in first.nodes] == [n.id for n in second.nodes]
    assert [e.key() for e in first.edges] == [e.key() for e in second.edges]
