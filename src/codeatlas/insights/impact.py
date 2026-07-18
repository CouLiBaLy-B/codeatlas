"""Analyse d'impact (FR-006, feature 003) : « qu'est-ce que ça touche ? ».

BFS inverse par niveaux sur les arêtes `calls` et `imports` : qui appelle, qui
importe, jusqu'à une profondeur donnée. Les points d'entrée atteints sont marqués ;
la certitude du lien traversé est conservée (jamais de fausse certitude).
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.insights.entrypoints import detect_entrypoints
from codeatlas.ir.model import CodeGraph, EdgeKind, NodeKind


@dataclass(frozen=True, slots=True)
class ImpactEntry:
    id: str
    via: str  # "calls" | "imports"
    certainty: str  # "certain" | "inferred"


@dataclass(frozen=True, slots=True)
class ImpactLevel:
    depth: int
    entries: tuple[ImpactEntry, ...]


@dataclass(frozen=True, slots=True)
class ImpactReport:
    targets: tuple[str, ...]
    levels: tuple[ImpactLevel, ...]
    entrypoints_reached: tuple[str, ...]


def compute_impact(graph: CodeGraph, targets: tuple[str, ...], depth: int) -> ImpactReport:
    """Rayon de propagation inverse depuis `targets`, par niveaux — déterministe."""
    reverse: dict[str, list[tuple[str, str, str]]] = {}
    for edge in graph.edges_of_kind(EdgeKind.CALLS, EdgeKind.IMPORTS):
        reverse.setdefault(edge.target, []).append(
            (edge.source, edge.kind.value, edge.certainty.value)
        )

    seen: set[str] = set(targets)
    frontier: set[str] = set(targets)
    levels: list[ImpactLevel] = []
    for current_depth in range(1, depth + 1):
        found: dict[str, ImpactEntry] = {}
        for node_id in sorted(frontier):
            for source, via, certainty in sorted(reverse.get(node_id, [])):
                if source in seen or source in found:
                    continue
                found[source] = ImpactEntry(id=source, via=via, certainty=certainty)
        if not found:
            break
        entries = tuple(found[key] for key in sorted(found))
        levels.append(ImpactLevel(depth=current_depth, entries=entries))
        seen.update(found)
        frontier = set(found)

    entry_ids: set[str] = set()
    for entry in detect_entrypoints(graph):
        node = graph.get_node(entry.node_id)
        if node is None:
            continue
        if node.kind in (NodeKind.FUNCTION, NodeKind.METHOD):
            entry_ids.add(node.id)
        elif node.kind is NodeKind.MODULE:
            entry_ids.add(node.id)
            if graph.get_node(f"{node.id}.main") is not None:
                entry_ids.add(f"{node.id}.main")

    affected = {e.id for level in levels for e in level.entries}
    return ImpactReport(
        targets=tuple(sorted(targets)),
        levels=tuple(levels),
        entrypoints_reached=tuple(sorted(affected & entry_ids)),
    )
