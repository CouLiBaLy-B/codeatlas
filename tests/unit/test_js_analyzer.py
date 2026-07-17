"""T067 — Tests contrat de l'analyseur JavaScript/TypeScript (mêmes exigences que T017)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas.analyzers.base import AnalyzerOptions, IRFragment, discover_files
from codeatlas.analyzers.javascript.analyzer import JavaScriptAnalyzer
from codeatlas.config import DEFAULT_EXCLUDES
from codeatlas.ir.model import Certainty, EdgeKind, NodeKind, SubProject, Visibility

CORPUS = Path(__file__).parents[2] / "examples" / "ts-demo"
SUB = SubProject(id="main", language="javascript", root=".")


@pytest.fixture(scope="module")
def fragment() -> IRFragment:
    analyzer = JavaScriptAnalyzer()
    files, unreadable = discover_files(CORPUS, DEFAULT_EXCLUDES, analyzer.extensions)
    assert not unreadable
    return analyzer.analyze(files, SUB, AnalyzerOptions())


class TestNodes:
    def test_modules_present_with_stable_ids(self, fragment: IRFragment) -> None:
        module_ids = {n.id for n in fragment.nodes if n.kind is NodeKind.MODULE}
        assert "main/src.models.product" in module_ids
        assert "main/src.services.catalog" in module_ids
        assert "main/src.server" in module_ids
        assert "main/src.broken" not in module_ids

    def test_classes_and_interface_detected(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        assert by_id["main/src.models.product.Product"].kind is NodeKind.CLASS
        assert by_id["main/src.models.product.DigitalProduct"].kind is NodeKind.CLASS
        assert by_id["main/src.models.product.ProductRepository"].kind is NodeKind.INTERFACE

    def test_methods_with_signature(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        method = by_id["main/src.models.product.Product.priceWithTax"]
        assert method.kind is NodeKind.METHOD
        assert "rate" in method.signature
        assert method.complexity is not None and method.complexity >= 1

    def test_free_function_extracted(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        assert by_id["main/src.services.catalog.formatLabel"].kind is NodeKind.FUNCTION

    def test_jsdoc_extracted_with_summary(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        doc = by_id["main/src.models.product.Product"].doc
        assert doc is not None
        assert doc.summary == "Un produit physique du catalogue."
        assert doc.format.value == "jsdoc"

    def test_private_visibility_from_ts_modifier(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        assert by_id["main/src.models.product.Product.rounded"].visibility is Visibility.PRIVATE
        assert by_id["main/src.services.catalog.CatalogService.repo"].visibility is (
            Visibility.PRIVATE
        )

    def test_route_registrations_recorded_on_module(self, fragment: IRFragment) -> None:
        by_id = {n.id: n for n in fragment.nodes}
        modifiers = by_id["main/src.server"].modifiers
        assert "route:GET /products" in modifiers
        assert "route:POST /products" in modifiers


class TestEdges:
    def test_inheritance_certain(self, fragment: IRFragment) -> None:
        inherits = [
            (e.source, e.target, e.certainty)
            for e in fragment.edges
            if e.kind is EdgeKind.INHERITS
        ]
        assert (
            "main/src.models.product.DigitalProduct",
            "main/src.models.product.Product",
            Certainty.CERTAIN,
        ) in inherits

    def test_relative_imports_resolved(self, fragment: IRFragment) -> None:
        imports = {
            (e.source, e.target) for e in fragment.edges if e.kind is EdgeKind.IMPORTS
        }
        assert ("main/src.services.catalog", "main/src.models.product") in imports
        assert ("main/src.server", "main/src.services.catalog") in imports


class TestTolerance:
    def test_invalid_file_skipped_with_reason(self, fragment: IRFragment) -> None:
        assert len(fragment.skipped) == 1
        entry = fragment.skipped[0]
        assert entry.path == "src/broken.ts"
        assert entry.reason


def test_determinism() -> None:
    analyzer = JavaScriptAnalyzer()
    files, _ = discover_files(CORPUS, DEFAULT_EXCLUDES, analyzer.extensions)
    first = analyzer.analyze(files, SUB, AnalyzerOptions())
    second = analyzer.analyze(files, SUB, AnalyzerOptions())
    assert [n.id for n in first.nodes] == [n.id for n in second.nodes]
    assert [e.key() for e in first.edges] == [e.key() for e in second.edges]
