"""Rapport d'exécution (FR-020) — synthèse d'une analyse/génération.

La durée n'apparaît QUE dans la console et le JSON de rapport, jamais dans les
artefacts versionnables (constitution I).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REPORT_VERSION = 1


@dataclass(frozen=True, slots=True)
class Warning_:
    code: str
    where: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    threshold: int
    actual: int
    passed: bool


@dataclass(slots=True)
class AnalysisReport:
    root: str
    subprojects: list[dict[str, Any]] = field(default_factory=list)
    files_analyzed: int = 0
    files_skipped: int = 0
    nodes: int = 0
    edges_certain: int = 0
    edges_inferred: int = 0
    skipped: list[dict[str, str]] = field(default_factory=list)
    warnings: list[Warning_] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Représentation stable pour --json-report (schéma : contracts/cli.md)."""
        return {
            "report_version": REPORT_VERSION,
            "root": self.root,
            "subprojects": self.subprojects,
            "counts": {
                "files_analyzed": self.files_analyzed,
                "files_skipped": self.files_skipped,
                "nodes": self.nodes,
                "edges_certain": self.edges_certain,
                "edges_inferred": self.edges_inferred,
            },
            "skipped": self.skipped,
            "warnings": [
                {"code": w.code, "where": w.where, "detail": w.detail} for w in self.warnings
            ],
            "checks": [
                {
                    "name": c.name,
                    "threshold": c.threshold,
                    "actual": c.actual,
                    "passed": c.passed,
                }
                for c in self.checks
            ],
            "duration_seconds": self.duration_seconds,
        }
