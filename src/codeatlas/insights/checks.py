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


def evaluate_regressions(delta: object, thresholds: CheckCfg) -> list[CheckResult]:
    """Règles de régression contre la baseline (feature 002) — opt-in.

    Une catégorie déjà présente dans la baseline n'est jamais une régression :
    seules les APPARITIONS (ou disparitions d'API) comptent.
    """
    from codeatlas.baseline.compare import ArchDelta

    assert isinstance(delta, ArchDelta)
    results: list[CheckResult] = []

    def appeared(name: str) -> int:
        category = delta.category(name)
        return len(category.appeared) if category is not None else 0

    def disappeared(name: str) -> int:
        category = delta.category(name)
        return len(category.disappeared) if category is not None else 0

    rules: list[tuple[bool, str, int]] = [
        (thresholds.fail_on_new_cycles, "fail-on-new-cycles", appeared("package_cycles")),
        (
            thresholds.fail_on_new_violations,
            "fail-on-new-violations",
            appeared("layer_violations"),
        ),
        (thresholds.fail_on_new_inferred, "fail-on-new-inferred", appeared("inferred_calls")),
        (
            thresholds.fail_on_removed_public_api,
            "fail-on-removed-public-api",
            disappeared("public_api"),
        ),
    ]
    for enabled, name, actual in rules:
        if enabled:
            results.append(
                CheckResult(name=name, threshold=0, actual=actual, passed=actual == 0)
            )

    if thresholds.max_doc_coverage_drop >= 0:
        drop = 0
        for metric in delta.metric_deltas:
            if metric.name == "doc_coverage":
                drop = max(0, metric.old - metric.new)
        results.append(
            CheckResult(
                name="max-doc-coverage-drop",
                threshold=thresholds.max_doc_coverage_drop,
                actual=drop,
                passed=drop <= thresholds.max_doc_coverage_drop,
            )
        )

    return sorted(results, key=lambda c: c.name)
