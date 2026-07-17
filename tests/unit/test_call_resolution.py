"""T034 — Résolution statique des appels : `certain` vs `inferred` (R6, FR-009)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas.analyzers.base import AnalyzerOptions, IRFragment, discover_files
from codeatlas.analyzers.python.analyzer import PythonAnalyzer
from codeatlas.config import DEFAULT_EXCLUDES
from codeatlas.ir.model import Certainty, EdgeKind, SubProject

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def fragment() -> IRFragment:
    analyzer = PythonAnalyzer()
    files, _ = discover_files(CORPUS, DEFAULT_EXCLUDES, analyzer.extensions)
    subproject = SubProject(id="main", language="python", root=".")
    return analyzer.analyze(files, subproject, AnalyzerOptions())


def calls(fragment: IRFragment, certainty: Certainty) -> set[tuple[str, str]]:
    return {
        (e.source, e.target)
        for e in fragment.edges
        if e.kind is EdgeKind.CALLS and e.certainty is certainty
    }


class TestCertainCalls:
    def test_direct_call_to_imported_function(self, fragment: IRFragment) -> None:
        assert (
            "main/shopdemo.cli.main",
            "main/shopdemo.quality.tangled_pricing",
        ) in calls(fragment, Certainty.CERTAIN)

    def test_constructor_call_targets_init(self, fragment: IRFragment) -> None:
        certain = calls(fragment, Certainty.CERTAIN)
        orders = "main/shopdemo.services.orders"
        order_mod = "main/shopdemo.models.order"
        assert ("main/shopdemo.cli.main", f"{orders}.OrderService.__init__") in certain
        assert (f"{order_mod}.Order.add", f"{order_mod}.OrderLine.__init__") in certain

    def test_method_call_via_local_variable_type(self, fragment: IRFragment) -> None:
        # service = OrderService() ; service.place(...)
        assert (
            "main/shopdemo.cli.main",
            "main/shopdemo.services.orders.OrderService.place",
        ) in calls(fragment, Certainty.CERTAIN)

    def test_chained_attribute_call_through_declared_types(self, fragment: IRFragment) -> None:
        # self.catalog.repo.find : OrderService → CatalogService → InMemoryRepo
        assert (
            "main/shopdemo.services.orders.OrderService.place",
            "main/shopdemo.storage.repo.InMemoryRepo.find",
        ) in calls(fragment, Certainty.CERTAIN)

    def test_call_on_annotated_attribute(self, fragment: IRFragment) -> None:
        # self.product.price_with_tax() — attribut annoté Product
        assert (
            "main/shopdemo.models.order.OrderLine.subtotal",
            "main/shopdemo.models.product.Product.price_with_tax",
        ) in calls(fragment, Certainty.CERTAIN)

    def test_call_on_annotated_parameter(self, fragment: IRFragment) -> None:
        # total_after_discount(order: Order) → order.total()
        assert (
            "main/shopdemo.services.orders.OrderService.total_after_discount",
            "main/shopdemo.models.order.Order.total",
        ) in calls(fragment, Certainty.CERTAIN)

    def test_call_through_module_level_variable(self, fragment: IRFragment) -> None:
        # _catalog = CatalogService(...) au niveau module de webapp
        assert (
            "main/shopdemo.webapp.create_product",
            "main/shopdemo.services.catalog.CatalogService.register",
        ) in calls(fragment, Certainty.CERTAIN)


class TestInferredCalls:
    def test_getattr_with_literal_yields_inferred_edge(self, fragment: IRFragment) -> None:
        assert (
            "main/shopdemo.legacy.pricing.refresh_catalog_price",
            "main/shopdemo.services.catalog.CatalogService.price_of",
        ) in calls(fragment, Certainty.INFERRED)

    def test_inferred_never_reported_as_certain(self, fragment: IRFragment) -> None:
        assert (
            "main/shopdemo.legacy.pricing.refresh_catalog_price",
            "main/shopdemo.services.catalog.CatalogService.price_of",
        ) not in calls(fragment, Certainty.CERTAIN)
