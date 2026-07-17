"""T017 — Tests contrat de l'analyseur Python sur le corpus python-demo."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas.analyzers.base import AnalyzerOptions, IRFragment, discover_files
from codeatlas.analyzers.python.analyzer import PythonAnalyzer
from codeatlas.config import DEFAULT_EXCLUDES
from codeatlas.ir.model import Certainty, EdgeKind, NodeKind, SubProject, Visibility

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"
SUB = SubProject(id="main", language="python", root=".")


@pytest.fixture(scope="module")
def fragment() -> IRFragment:
    analyzer = PythonAnalyzer()
    files, unreadable = discover_files(CORPUS, DEFAULT_EXCLUDES, analyzer.extensions)
    assert not unreadable
    return analyzer.analyze(files, SUB, AnalyzerOptions())


def edges_of(fragment: IRFragment, kind: EdgeKind) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in fragment.edges if e.kind is kind}


class TestNodes:
    def test_all_modules_present_with_stable_ids(self, fragment: IRFragment) -> None:
        module_ids = {n.id for n in fragment.nodes if n.kind is NodeKind.MODULE}
        assert "main/shopdemo.models.product" in module_ids
        assert "main/shopdemo.services.catalog" in module_ids
        assert "main/shopdemo" in module_ids  # __init__.py → module du package
        assert "main/shopdemo.broken.invalid_syntax" not in module_ids

    def test_init_modules_carry_package_modifier(self, fragment: IRFragment) -> None:
        nodes = {n.id: n for n in fragment.nodes}
        assert "package" in nodes["main/shopdemo.models"].modifiers
        assert "package" not in nodes["main/shopdemo.models.product"].modifiers

    def test_all_corpus_classes_found(self, fragment: IRFragment) -> None:
        class_names = {n.name for n in fragment.nodes if n.kind is NodeKind.CLASS}
        assert class_names == {
            "Product",
            "DigitalProduct",
            "_ProductCache",
            "OrderLine",
            "Order",
            "InMemoryRepo",
            "CatalogService",
            "OrderService",
        }

    def test_methods_attached_with_signature(self, fragment: IRFragment) -> None:
        nodes = {n.id: n for n in fragment.nodes}
        method = nodes["main/shopdemo.models.product.Product.price_with_tax"]
        assert method.kind is NodeKind.METHOD
        assert "rate: float = 0.2" in method.signature
        assert "-> float" in method.signature

    def test_visibility_follows_underscore_convention(self, fragment: IRFragment) -> None:
        nodes = {n.id: n for n in fragment.nodes}
        product = "main/shopdemo.models.product"
        assert nodes[f"{product}._ProductCache"].visibility is Visibility.PRIVATE
        assert nodes[f"{product}.Product._rounded"].visibility is Visibility.PRIVATE
        assert nodes[f"{product}.Product"].visibility is Visibility.PUBLIC
        # dunder = public par convention
        assert nodes[f"{product}.Product.__init__"].visibility is Visibility.PUBLIC

    def test_docstrings_extracted_with_summary(self, fragment: IRFragment) -> None:
        nodes = {n.id: n for n in fragment.nodes}
        doc = nodes["main/shopdemo.models.product.Product"].doc
        assert doc is not None
        assert doc.summary == "Un produit physique du catalogue."
        assert nodes["main/shopdemo.storage.repo.InMemoryRepo.find"].doc is None

    def test_attributes_extracted(self, fragment: IRFragment) -> None:
        attr_ids = {n.id for n in fragment.nodes if n.kind is NodeKind.ATTRIBUTE}
        assert "main/shopdemo.models.product.Product.price" in attr_ids
        assert "main/shopdemo.models.order.OrderLine.product" in attr_ids

    def test_complexity_computed_for_functions(self, fragment: IRFragment) -> None:
        nodes = {n.id: n for n in fragment.nodes}
        simple = nodes["main/shopdemo.models.product.Product.price_with_tax"]
        branchy = nodes["main/shopdemo.services.catalog.CatalogService.register"]
        assert simple.complexity == 1
        assert branchy.complexity is not None and branchy.complexity >= 2
        assert nodes["main/shopdemo.models.product.Product"].complexity is None


class TestEdges:
    def test_inheritance_detected_as_certain(self, fragment: IRFragment) -> None:
        inherits = [e for e in fragment.edges if e.kind is EdgeKind.INHERITS]
        assert [(e.source, e.target) for e in inherits] == [
            (
                "main/shopdemo.models.product.DigitalProduct",
                "main/shopdemo.models.product.Product",
            )
        ]
        assert inherits[0].certainty is Certainty.CERTAIN

    def test_composition_from_instantiation_in_class(self, fragment: IRFragment) -> None:
        composes = edges_of(fragment, EdgeKind.COMPOSES)
        assert (
            "main/shopdemo.models.order.Order",
            "main/shopdemo.models.order.OrderLine",
        ) in composes
        assert (
            "main/shopdemo.services.orders.OrderService",
            "main/shopdemo.services.catalog.CatalogService",
        ) in composes

    def test_aggregation_from_constructor_parameter(self, fragment: IRFragment) -> None:
        assert (
            "main/shopdemo.services.catalog.CatalogService",
            "main/shopdemo.storage.repo.InMemoryRepo",
        ) in edges_of(fragment, EdgeKind.AGGREGATES)

    def test_association_from_typed_attribute(self, fragment: IRFragment) -> None:
        assert (
            "main/shopdemo.models.order.OrderLine",
            "main/shopdemo.models.product.Product",
        ) in edges_of(fragment, EdgeKind.ASSOCIATES)

    def test_imports_between_modules(self, fragment: IRFragment) -> None:
        imports = edges_of(fragment, EdgeKind.IMPORTS)
        assert ("main/shopdemo.models.order", "main/shopdemo.models.product") in imports
        assert ("main/shopdemo.legacy.pricing", "main/shopdemo.services.catalog") in imports
        assert ("main/shopdemo.services.orders", "main/shopdemo.legacy.pricing") in imports
        # import local à une fonction (dans _default_repo)
        assert ("main/shopdemo.services.orders", "main/shopdemo.storage.repo") in imports


class TestTolerance:
    def test_invalid_file_is_skipped_with_reason_not_raised(self, fragment: IRFragment) -> None:
        assert len(fragment.skipped) == 1
        entry = fragment.skipped[0]
        assert entry.path == "shopdemo/broken/invalid_syntax.py"
        assert "SyntaxError" in entry.reason

    def test_paths_are_posix_relative(self, fragment: IRFragment) -> None:
        for node in fragment.nodes:
            assert not node.location.file.startswith("/")
            assert "\\" not in node.location.file


class TestDeterminism:
    def test_two_runs_produce_identical_fragments(self, fragment: IRFragment) -> None:
        analyzer = PythonAnalyzer()
        files, _ = discover_files(CORPUS, DEFAULT_EXCLUDES, analyzer.extensions)
        again = analyzer.analyze(files, SUB, AnalyzerOptions())
        assert [n.id for n in again.nodes] == [n.id for n in fragment.nodes]
        assert [e.key() for e in again.edges] == [e.key() for e in fragment.edges]
