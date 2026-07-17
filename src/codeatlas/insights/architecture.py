"""Détection de couches et de violations d'architecture (FR-013, R7).

Heuristique transparente : les packages sont assignés à une couche par convention
de nommage, puis chaque dépendance de package remontant l'ordre des couches est
une violation, justifiée par les imports de modules qui la matérialisent.
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.graph.algorithms import module_package, package_dependencies
from codeatlas.ir.model import CodeGraph, EdgeKind, NodeKind

# vocabulaire → niveau (plus haut = plus proche de l'utilisateur)
_LAYER_VOCABULARY: dict[str, tuple[str, int]] = {
    # présentation
    "api": ("api", 3),
    "routes": ("api", 3),
    "views": ("api", 3),
    "controllers": ("api", 3),
    "web": ("api", 3),
    "ui": ("api", 3),
    "cli": ("api", 3),
    # métier
    "domain": ("domain", 2),
    "core": ("domain", 2),
    "services": ("domain", 2),
    "business": ("domain", 2),
    "usecases": ("domain", 2),
    "models": ("domain", 2),
    # infrastructure
    "infra": ("infra", 1),
    "infrastructure": ("infra", 1),
    "storage": ("infra", 1),
    "db": ("infra", 1),
    "database": ("infra", 1),
    "persistence": ("infra", 1),
    "adapters": ("infra", 1),
    "repositories": ("infra", 1),
}


@dataclass(frozen=True, slots=True)
class Layer:
    name: str
    level: int
    packages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LayerViolation:
    source_package: str
    target_package: str
    evidence: tuple[str, ...]  # imports de modules matérialisant la dépendance


@dataclass(frozen=True, slots=True)
class ArchitectureReport:
    layers: tuple[Layer, ...]
    violations: tuple[LayerViolation, ...]


def _layer_of(package: str) -> tuple[str, int] | None:
    """Couche d'un package d'après ses segments (le plus profond gagne)."""
    assigned: tuple[str, int] | None = None
    for part in package.split("."):
        if part in _LAYER_VOCABULARY:
            assigned = _LAYER_VOCABULARY[part]
    return assigned


def _import_evidence(graph: CodeGraph, source_pkg: str, target_pkg: str) -> tuple[str, ...]:
    """Imports module → module qui matérialisent une dépendance de packages."""
    module_ids = {n.id for n in graph.iter_nodes(NodeKind.MODULE)}
    found = []
    for edge in graph.edges_of_kind(EdgeKind.IMPORTS):
        if edge.source not in module_ids or edge.target not in module_ids:
            continue
        source_q = edge.source.split("/", 1)[-1]
        target_q = edge.target.split("/", 1)[-1]
        if module_package(source_q) == source_pkg and module_package(target_q) == target_pkg:
            found.append(f"{source_q} → {target_q}")
    return tuple(sorted(found))


def compute_architecture(graph: CodeGraph) -> ArchitectureReport:
    """Couches détectées + dépendances violant leur ordre — déterministe."""
    dependencies = package_dependencies(graph)
    packages = sorted(
        {p for pair in dependencies for p in pair}
        | {
            module_package(n.id.split("/", 1)[-1])
            for n in graph.iter_nodes(NodeKind.MODULE)
        }
    )

    assignment: dict[str, tuple[str, int]] = {}
    for package in packages:
        layer = _layer_of(package)
        if layer is not None:
            assignment[package] = layer

    grouped: dict[tuple[str, int], list[str]] = {}
    for package, layer in assignment.items():
        grouped.setdefault(layer, []).append(package)
    layers = tuple(
        Layer(name=name, level=level, packages=tuple(sorted(pkgs)))
        for (name, level), pkgs in sorted(grouped.items(), key=lambda kv: -kv[0][1])
    )

    violations = []
    for source_pkg, target_pkg in dependencies:
        source_layer = assignment.get(source_pkg)
        target_layer = assignment.get(target_pkg)
        if source_layer is None or target_layer is None:
            continue
        if source_layer[1] < target_layer[1]:  # dépendance qui REMONTE les couches
            violations.append(
                LayerViolation(
                    source_package=source_pkg,
                    target_package=target_pkg,
                    evidence=_import_evidence(graph, source_pkg, target_pkg),
                )
            )
    return ArchitectureReport(
        layers=layers,
        violations=tuple(sorted(violations, key=lambda v: (v.source_package, v.target_package))),
    )
