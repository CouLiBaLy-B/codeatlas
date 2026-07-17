"""Métriques de santé calculées sur l'IR (FR-012, R5).

Complexité (fournie par les analyseurs sur les nœuds), taille, couplage
(fan-in/fan-out des imports), couverture de documentation interne. Statuts dérivés
des seuils configurables ([metrics] de codeatlas.toml).
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.config import Config
from codeatlas.ir.model import CodeGraph, EdgeKind, Node, NodeKind, Visibility

STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_CRITICAL = "critical"

_STATUS_ORDER = {STATUS_OK: 0, STATUS_WARN: 1, STATUS_CRITICAL: 2}


@dataclass(frozen=True, slots=True)
class SymbolMetric:
    node_id: str
    name: str
    value: int
    status: str


@dataclass(frozen=True, slots=True)
class ModuleHealth:
    module_id: str
    loc: int
    functions: int
    max_complexity: int
    doc_coverage: int  # % de symboles publics documentés
    fan_in: int
    fan_out: int
    status: str


@dataclass(frozen=True, slots=True)
class HealthReport:
    modules: tuple[ModuleHealth, ...]
    worst_functions: tuple[SymbolMetric, ...]
    global_doc_coverage: int


def _complexity_status(value: int, config: Config) -> str:
    if value > config.metrics.complexity_critical:
        return STATUS_CRITICAL
    if value > config.metrics.complexity_warn:
        return STATUS_WARN
    return STATUS_OK


def _worst(*statuses: str) -> str:
    return max(statuses, key=lambda s: _STATUS_ORDER[s])


def _is_documentable(node: Node) -> bool:
    if node.name.startswith("__") and node.name.endswith("__"):
        return False  # documenter un dunder est optionnel par convention
    return (
        node.visibility is Visibility.PUBLIC
        and node.kind
        in (NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM, NodeKind.FUNCTION, NodeKind.METHOD)
    )


def compute_metrics(graph: CodeGraph, config: Config) -> HealthReport:
    """Tableau de bord santé : une ligne par module + pires fonctions."""
    modules = list(graph.iter_nodes(NodeKind.MODULE))
    fan_in: dict[str, int] = {m.id: 0 for m in modules}
    fan_out: dict[str, int] = {m.id: 0 for m in modules}
    for edge in graph.edges_of_kind(EdgeKind.IMPORTS):
        if edge.source in fan_out:
            fan_out[edge.source] += 1
        if edge.target in fan_in:
            fan_in[edge.target] += 1

    rows: list[ModuleHealth] = []
    worst_functions: list[SymbolMetric] = []
    documented_total = 0
    documentable_total = 0

    for module in modules:
        # membres = symboles définis dans le MÊME fichier (pas les sous-modules)
        members = [
            n
            for n in graph.iter_nodes()
            if n.location.file == module.location.file and n.id != module.id
        ]

        complexities = [
            n.complexity for n in members if n.complexity is not None
        ]
        max_complexity = max(complexities, default=0)

        documentable = [n for n in members if _is_documentable(n)]
        documented = [n for n in documentable if n.doc is not None]
        documentable_total += len(documentable)
        documented_total += len(documented)
        doc_coverage = (
            round(100 * len(documented) / len(documentable)) if documentable else 100
        )

        for node in members:
            if node.complexity is None:
                continue
            status = _complexity_status(node.complexity, config)
            if status != STATUS_OK:
                worst_functions.append(
                    SymbolMetric(
                        node_id=node.id,
                        name="complexity",
                        value=node.complexity,
                        status=status,
                    )
                )

        doc_status = (
            STATUS_WARN if doc_coverage < config.metrics.doc_coverage_warn else STATUS_OK
        )
        rows.append(
            ModuleHealth(
                module_id=module.id,
                loc=module.loc,
                functions=sum(
                    1 for n in members if n.kind in (NodeKind.FUNCTION, NodeKind.METHOD)
                ),
                max_complexity=max_complexity,
                doc_coverage=doc_coverage,
                fan_in=fan_in[module.id],
                fan_out=fan_out[module.id],
                status=_worst(_complexity_status(max_complexity, config), doc_status),
            )
        )

    worst_functions.sort(key=lambda m: (-m.value, m.node_id))
    global_coverage = (
        round(100 * documented_total / documentable_total) if documentable_total else 100
    )
    return HealthReport(
        modules=tuple(sorted(rows, key=lambda r: r.module_id)),
        worst_functions=tuple(worst_functions),
        global_doc_coverage=global_coverage,
    )
