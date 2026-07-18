"""Parcours de lecture (FR-007, feature 003) — ordre d'onboarding déterministe.

Purement structurel : modules des points d'entrée d'abord, puis les couches de la
plus haute (présentation) à la plus basse (infrastructure), non assignés en dernier,
alphabétique dans chaque groupe. Aucune narration : la sémantique reste à
l'assistant de l'utilisateur.
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.config import Config
from codeatlas.graph.algorithms import module_package
from codeatlas.insights.architecture import compute_architecture
from codeatlas.insights.entrypoints import detect_entrypoints
from codeatlas.ir.model import CodeGraph, NodeKind


@dataclass(frozen=True, slots=True)
class TourStep:
    module: str  # qualname affiché
    reason: str
    page: str  # page de documentation correspondante


def reading_tour(graph: CodeGraph, config: Config) -> tuple[TourStep, ...]:
    """Étapes ordonnées et déterministes du parcours de lecture."""
    from codeatlas.site.pages import module_display_name, page_slug

    entry_module_ids: set[str] = set()
    for entry in detect_entrypoints(graph):
        node = graph.get_node(entry.node_id)
        if node is None:
            continue
        if node.kind is NodeKind.MODULE:
            entry_module_ids.add(node.id)
        else:
            entry_module_ids.add(node.id.rsplit(".", 1)[0])

    layer_of_package: dict[str, tuple[str, int]] = {}
    for layer in compute_architecture(graph).layers:
        for package in layer.packages:
            layer_of_package[package] = (layer.name, layer.level)

    steps: list[TourStep] = []
    visited: set[str] = set()

    def add(module_id: str, reason: str) -> None:
        if module_id in visited:
            return
        visited.add(module_id)
        steps.append(
            TourStep(
                module=module_display_name(graph, module_id),
                reason=reason,
                page=f"modules/{page_slug(graph, module_id)}.md",
            )
        )

    modules = list(graph.iter_nodes(NodeKind.MODULE))
    for module in modules:
        if module.id in entry_module_ids:
            add(module.id, "point d'entrée")

    remaining = [m for m in modules if m.id not in visited]
    with_layer: list[tuple[int, str, str]] = []
    without_layer: list[str] = []
    for module in remaining:
        package = module_package(module.id.split("/", 1)[-1])
        assigned = layer_of_package.get(package)
        if assigned is not None:
            layer_name, level = assigned
            with_layer.append((-level, module.id, layer_name))
        else:
            without_layer.append(module.id)
    for _, module_id, layer_name in sorted(with_layer):
        add(module_id, f"couche {layer_name}")
    for module_id in sorted(without_layer):
        add(module_id, "autres")

    return tuple(steps)
