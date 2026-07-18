"""Capture de la baseline : CodeGraph + insights → résumé architectural canonique.

Contrat : specs/002-architectural-diff/contracts/baseline-schema.md.
Dérivé exclusivement de l'IR et des insights existants (constitution III) —
mêmes définitions que le site, aucun horodatage (constitution I).
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.config import Config
from codeatlas.graph.algorithms import package_cycles
from codeatlas.insights.architecture import compute_architecture
from codeatlas.insights.deadcode import find_dead_code
from codeatlas.insights.metrics import STATUS_CRITICAL, compute_metrics
from codeatlas.ir.model import IR_VERSION, Certainty, CodeGraph, EdgeKind, NodeKind, Visibility

BASELINE_VERSION = 1

_API_KINDS = (
    NodeKind.CLASS,
    NodeKind.INTERFACE,
    NodeKind.ENUM,
    NodeKind.FUNCTION,
    NodeKind.METHOD,
)


@dataclass(frozen=True, slots=True)
class ApiEntry:
    id: str
    kind: str
    signature: str


@dataclass(frozen=True, slots=True)
class Baseline:
    """Résumé architectural versionnable — canonique et sans horodatage."""

    baseline_version: int
    ir_version: int
    root: str
    subprojects: tuple[tuple[str, str], ...]  # (id, language)
    public_api: tuple[ApiEntry, ...]
    package_cycles: tuple[tuple[str, ...], ...]
    layer_violations: tuple[tuple[str, str], ...]  # (source, target)
    inferred_calls: tuple[tuple[str, str], ...]  # (source, target)
    dead_code: tuple[tuple[str, str], ...]  # (id, confidence)
    service_deps: tuple[tuple[str, str], ...]  # (source, target)
    skipped: tuple[tuple[str, str], ...]  # (path, reason)
    metrics: tuple[tuple[str, int], ...]  # triées par nom

    def metric(self, name: str) -> int:
        return dict(self.metrics)[name]

    @property
    def metrics_dict(self) -> dict[str, int]:
        return dict(self.metrics)


def capture(graph: CodeGraph, config: Config) -> Baseline:
    """Capture l'état architectural courant — déterministe."""
    public_api = tuple(
        ApiEntry(id=node.id, kind=node.kind.value, signature=node.signature)
        for node in graph.iter_nodes()
        if node.kind in _API_KINDS and node.visibility is Visibility.PUBLIC
    )

    health = compute_metrics(graph, config)
    architecture = compute_architecture(graph)
    dead = find_dead_code(graph)

    metrics = {
        "files_analyzed": sum(1 for _ in graph.iter_nodes(NodeKind.MODULE)),
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "doc_coverage": health.global_doc_coverage,
        "critical_symbols": sum(
            1 for fn in health.worst_functions if fn.status == STATUS_CRITICAL
        ),
    }

    return Baseline(
        baseline_version=BASELINE_VERSION,
        ir_version=IR_VERSION,
        root=graph.root,
        subprojects=tuple(sorted((s.id, s.language) for s in graph.subprojects)),
        public_api=tuple(sorted(public_api, key=lambda e: e.id)),
        package_cycles=tuple(tuple(cycle) for cycle in package_cycles(graph)),
        layer_violations=tuple(
            (v.source_package, v.target_package) for v in architecture.violations
        ),
        inferred_calls=tuple(
            sorted(
                (e.source, e.target)
                for e in graph.edges_of_kind(EdgeKind.CALLS)
                if e.certainty is Certainty.INFERRED
            )
        ),
        dead_code=tuple((c.node_id, c.confidence) for c in dead),
        service_deps=tuple(
            sorted((e.source, e.target) for e in graph.edges_of_kind(EdgeKind.SERVICE_DEP))
        ),
        skipped=tuple((s.path, s.reason) for s in graph.skipped),
        metrics=tuple(sorted(metrics.items())),
    )
