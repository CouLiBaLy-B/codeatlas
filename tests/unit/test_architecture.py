"""T058 — Détection de couches et de violations d'architecture (FR-013, R7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.insights.architecture import ArchitectureReport, compute_architecture
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "layered-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


@pytest.fixture(scope="module")
def report(graph: CodeGraph) -> ArchitectureReport:
    return compute_architecture(graph)


class TestLayers:
    def test_three_layers_detected(self, report: ArchitectureReport) -> None:
        by_name = {layer.name: layer for layer in report.layers}
        assert "api" in by_name
        assert "domain" in by_name
        assert "infra" in by_name

    def test_layer_levels_ordered_top_to_bottom(self, report: ArchitectureReport) -> None:
        by_name = {layer.name: layer.level for layer in report.layers}
        assert by_name["api"] > by_name["domain"] > by_name["infra"]

    def test_packages_assigned_to_layers(self, report: ArchitectureReport) -> None:
        by_name = {layer.name: layer for layer in report.layers}
        assert "webshop.api" in by_name["api"].packages
        assert "webshop.domain" in by_name["domain"].packages
        assert "webshop.infra" in by_name["infra"].packages


class TestViolations:
    def test_upward_dependency_flagged(self, report: ArchitectureReport) -> None:
        pairs = {(v.source_package, v.target_package) for v in report.violations}
        assert ("webshop.infra", "webshop.api") in pairs

    def test_violation_carries_evidence(self, report: ArchitectureReport) -> None:
        violation = next(
            v for v in report.violations if v.source_package == "webshop.infra"
        )
        assert violation.evidence  # FR-013 : jamais de détection sans indice
        assert any("legacy_bridge" in item for item in violation.evidence)

    def test_downward_dependencies_allowed(self, report: ArchitectureReport) -> None:
        pairs = {(v.source_package, v.target_package) for v in report.violations}
        assert ("webshop.api", "webshop.domain") not in pairs
        assert ("webshop.domain", "webshop.infra") not in pairs


def test_determinism(graph: CodeGraph) -> None:
    assert compute_architecture(graph) == compute_architecture(graph)
