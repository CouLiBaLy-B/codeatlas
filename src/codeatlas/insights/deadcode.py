"""Code probablement mort (FR-012, R7) : atteignabilité + références entrantes.

Un symbole est candidat s'il n'est PAS atteignable depuis les points d'entrée via
le graphe d'appels (toutes certitudes confondues) ET n'a aucune référence entrante.
La confiance est dégradée pour les symboles publics (importables de l'extérieur) ;
les dunders ne sont jamais signalés.
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.graph.algorithms import reachable_from
from codeatlas.insights.entrypoints import detect_entrypoints
from codeatlas.ir.model import CodeGraph, EdgeKind, NodeKind, Visibility


@dataclass(frozen=True, slots=True)
class DeadCodeCandidate:
    node_id: str
    confidence: str  # "high" (privé) | "medium" (public)
    reason: str


def find_dead_code(graph: CodeGraph) -> tuple[DeadCodeCandidate, ...]:
    """Fonctions et méthodes probablement mortes, triées par id — déterministe."""
    call_edges = [
        (e.source, e.target) for e in graph.edges_of_kind(EdgeKind.CALLS)
    ]
    referenced = {e.target for e in graph.edges_of_kind(EdgeKind.CALLS, EdgeKind.REFERENCES)}

    roots: set[str] = set()
    for entry in detect_entrypoints(graph):
        node = graph.get_node(entry.node_id)
        if node is None:
            continue
        if node.kind in (NodeKind.FUNCTION, NodeKind.METHOD):
            roots.add(entry.node_id)
        elif node.kind is NodeKind.MODULE and graph.get_node(f"{entry.node_id}.main"):
            roots.add(f"{entry.node_id}.main")

    alive = reachable_from(call_edges, sorted(roots))

    candidates: list[DeadCodeCandidate] = []
    for kind in (NodeKind.FUNCTION, NodeKind.METHOD):
        for node in graph.iter_nodes(kind):
            if node.name.startswith("__") and node.name.endswith("__"):
                continue  # dunder : appelé implicitement par le langage
            if node.id in alive or node.id in referenced:
                continue
            private = node.visibility is Visibility.PRIVATE
            candidates.append(
                DeadCodeCandidate(
                    node_id=node.id,
                    confidence="high" if private else "medium",
                    reason=(
                        "non atteignable depuis les points d'entrée et jamais référencé"
                        + ("" if private else " (mais public : usage externe possible)")
                    ),
                )
            )
    return tuple(sorted(candidates, key=lambda c: c.node_id))
