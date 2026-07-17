"""T050 — Mode check (FR-018) : chaque seuil passe/échoue, seuils absents ignorés."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.config import CheckCfg, Config
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


def run(graph: CodeGraph, **thresholds: int) -> dict[str, tuple[int, int, bool]]:
    results = api.run_checks(graph, CheckCfg(**thresholds), Config())
    return {c.name: (c.threshold, c.actual, c.passed) for c in results}


class TestPackageCycles:
    def test_cycle_over_threshold_fails(self, graph: CodeGraph) -> None:
        results = run(graph, max_package_cycles=0)
        threshold, actual, passed = results["max-package-cycles"]
        assert (threshold, actual, passed) == (0, 1, False)

    def test_cycle_within_threshold_passes(self, graph: CodeGraph) -> None:
        assert run(graph, max_package_cycles=1)["max-package-cycles"][2] is True


class TestDocCoverage:
    def test_low_requirement_passes(self, graph: CodeGraph) -> None:
        assert run(graph, min_doc_coverage=10)["min-doc-coverage"][2] is True

    def test_high_requirement_fails(self, graph: CodeGraph) -> None:
        assert run(graph, min_doc_coverage=99)["min-doc-coverage"][2] is False


class TestCriticalSymbols:
    def test_critical_function_fails_zero_threshold(self, graph: CodeGraph) -> None:
        _, actual, passed = run(graph, max_critical_symbols=0)["max-critical-symbols"]
        assert actual >= 1  # tangled_pricing
        assert passed is False

    def test_generous_threshold_passes(self, graph: CodeGraph) -> None:
        assert run(graph, max_critical_symbols=5)["max-critical-symbols"][2] is True


class TestUnsetThresholds:
    def test_unset_thresholds_emit_no_check(self, graph: CodeGraph) -> None:
        assert run(graph) == {}

    def test_only_configured_checks_run(self, graph: CodeGraph) -> None:
        results = run(graph, min_doc_coverage=10)
        assert set(results) == {"min-doc-coverage"}
