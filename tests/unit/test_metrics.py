"""T044 — Métriques de santé : complexité, taille, couplage, couverture doc (FR-012)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.config import Config
from codeatlas.insights.metrics import HealthReport, compute_metrics
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


@pytest.fixture(scope="module")
def health(graph: CodeGraph) -> HealthReport:
    return compute_metrics(graph, Config())


def module_row(health: HealthReport, module_id: str):
    rows = {m.module_id: m for m in health.modules}
    return rows[module_id]


class TestComplexity:
    def test_tangled_function_is_critical(self, health: HealthReport) -> None:
        worst = {m.node_id: m for m in health.worst_functions}
        entry = worst["main/shopdemo.quality.tangled_pricing"]
        assert entry.value > 20
        assert entry.status == "critical"

    def test_simple_functions_not_reported_as_worst(self, health: HealthReport) -> None:
        worst_ids = {m.node_id for m in health.worst_functions}
        assert "main/shopdemo.models.product.Product.price_with_tax" not in worst_ids

    def test_module_max_complexity(self, health: HealthReport) -> None:
        assert module_row(health, "main/shopdemo.quality").max_complexity > 20
        assert module_row(health, "main/shopdemo.quality").status == "critical"


class TestDocCoverage:
    def test_quality_module_coverage_is_half(self, health: HealthReport) -> None:
        # public : tangled_pricing (doc) + forgotten_public_api (sans doc) → 50 %
        assert module_row(health, "main/shopdemo.quality").doc_coverage == 50

    def test_fully_documented_module(self, health: HealthReport) -> None:
        assert module_row(health, "main/shopdemo.models.order").doc_coverage == 100

    def test_global_coverage_bounded(self, health: HealthReport) -> None:
        assert 0 < health.global_doc_coverage < 100


class TestCoupling:
    def test_fan_in_and_fan_out_from_imports(self, health: HealthReport) -> None:
        repo = module_row(health, "main/shopdemo.storage.repo")
        assert repo.fan_in >= 3  # importé par catalog, orders, webapp
        assert repo.fan_out == 1  # importe models.product


class TestDeterminism:
    def test_two_computations_identical(self, graph: CodeGraph) -> None:
        assert compute_metrics(graph, Config()) == compute_metrics(graph, Config())
