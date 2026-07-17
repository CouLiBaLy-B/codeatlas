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


class TestCalls:
    """T083 — arêtes `calls` extraites par l'analyseur Java (FR-009)."""

    def _calls(self, fragment: IRFragment) -> set[tuple[str, str]]:
        return {(e.source, e.target) for e in fragment.edges if e.kind is EdgeKind.CALLS}

    def test_local_variable_typed_call(self, fragment: IRFragment) -> None:
        assert (
            "main/com.shop.Application.Application.main",
            "main/com.shop.CatalogService.CatalogService.register",
        ) in self._calls(fragment)

    def test_constructor_call_via_new(self, fragment: IRFragment) -> None:
        assert (
            "main/com.shop.Application.Application.main",
            "main/com.shop.Product.Product.Product",
        ) in self._calls(fragment)

    def test_field_call_through_this(self, fragment: IRFragment) -> None:
        assert (
            "main/com.shop.ShopController.ShopController.createProduct",
            "main/com.shop.CatalogService.CatalogService.register",
        ) in self._calls(fragment)

    def test_annotated_parameter_call(self, fragment: IRFragment) -> None:
        assert (
            "main/com.shop.CatalogService.CatalogService.register",
            "main/com.shop.Product.Product.getName",
        ) in self._calls(fragment)

    def test_super_call_targets_parent(self, fragment: IRFragment) -> None:
        assert (
            "main/com.shop.DigitalProduct.DigitalProduct.priceWithTax",
            "main/com.shop.Product.Product.priceWithTax",
        ) in self._calls(fragment)


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
