"""Mode « check » (FR-018) : seuils qualité pour la CI, exit 3 en cas de violation.

Un seuil à -1 n'est pas vérifié : seuls les seuils explicitement configurés
produisent un CheckResult.
"""

from __future__ import annotations

from codeatlas.config import CheckCfg, Config
from codeatlas.graph.algorithms import package_cycles
from codeatlas.insights.metrics import STATUS_CRITICAL, compute_metrics
from codeatlas.ir.model import CodeGraph
from codeatlas.report.model import CheckResult


def run_checks(graph: CodeGraph, thresholds: CheckCfg, config: Config) -> list[CheckResult]:
    """Évalue les seuils configurés — liste triée par nom, déterministe."""
    results: list[CheckResult] = []

    if thresholds.max_package_cycles >= 0:
        actual = len(package_cycles(graph))
        results.append(
            CheckResult(
                name="max-package-cycles",
                threshold=thresholds.max_package_cycles,
                actual=actual,
                passed=actual <= thresholds.max_package_cycles,
            )
        )

    needs_metrics = thresholds.min_doc_coverage >= 0 or thresholds.max_critical_symbols >= 0
    if needs_metrics:
        health = compute_metrics(graph, config)
        if thresholds.min_doc_coverage >= 0:
            results.append(
                CheckResult(
                    name="min-doc-coverage",
                    threshold=thresholds.min_doc_coverage,
                    actual=health.global_doc_coverage,
                    passed=health.global_doc_coverage >= thresholds.min_doc_coverage,
                )
            )
        if thresholds.max_critical_symbols >= 0:
            critical = sum(
                1 for fn in health.worst_functions if fn.status == STATUS_CRITICAL
            )
            results.append(
                CheckResult(
                    name="max-critical-symbols",
                    threshold=thresholds.max_critical_symbols,
                    actual=critical,
                    passed=critical <= thresholds.max_critical_symbols,
                )
            )

    return sorted(results, key=lambda c: c.name)
