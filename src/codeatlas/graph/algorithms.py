"""Algorithmes de graphe sur l'IR — networkx est confiné à ce module.

Toutes les sorties sont triées : le déterminisme est garanti ici, pas par networkx.
"""

from __future__ import annotations

from collections.abc import Iterable

import networkx as nx

from codeatlas.ir.model import CodeGraph, EdgeKind, NodeKind


def _digraph(edges: Iterable[tuple[str, str]]) -> nx.DiGraph:
    graph: nx.DiGraph = nx.DiGraph()
    graph.add_edges_from(sorted(set(edges)))
    return graph


def find_cycles(edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    """Cycles (composantes fortement connexes non triviales), normalisés et triés.

    Chaque cycle est la liste triée de ses nœuds ; les cycles sont triés entre eux.
    Une auto-boucle est un cycle de taille 1.
    """
    graph = _digraph(edges)
    cycles: list[list[str]] = []
    for component in nx.strongly_connected_components(graph):
        if len(component) > 1:
            cycles.append(sorted(component))
        else:
            (node,) = component
            if graph.has_edge(node, node):
                cycles.append([node])
    return sorted(cycles)


def reachable_from(edges: Iterable[tuple[str, str]], sources: Iterable[str]) -> frozenset[str]:
    """Ensemble des nœuds atteignables depuis `sources` (sources incluses)."""
    graph = _digraph(edges)
    seen: set[str] = set()
    for source in sources:
        seen.add(source)
        if graph.has_node(source):
            seen.update(nx.descendants(graph, source))
    return frozenset(seen)


def module_package(module_qualname: str) -> str:
    """`app.services.catalog` → `app.services` ; module racine → lui-même."""
    return module_qualname.rsplit(".", 1)[0] if "." in module_qualname else module_qualname


def _module_qualname(node_id: str) -> str:
    """Retire le préfixe sous-projet d'un id de module (`main/app.mod` → `app.mod`)."""
    return node_id.split("/", 1)[1] if "/" in node_id else node_id


def package_dependencies(graph: CodeGraph) -> list[tuple[str, str]]:
    """Arêtes de dépendance entre packages, agrégées depuis les imports de modules.

    Les dépendances internes à un même package sont exclues.
    """
    module_ids = {n.id for n in graph.iter_nodes(NodeKind.MODULE)}
    pairs: set[tuple[str, str]] = set()
    for edge in graph.edges_of_kind(EdgeKind.IMPORTS):
        if edge.source not in module_ids or edge.target not in module_ids:
            continue
        src = module_package(_module_qualname(edge.source))
        dst = module_package(_module_qualname(edge.target))
        if src != dst:
            pairs.add((src, dst))
    return sorted(pairs)


def package_cycles(graph: CodeGraph) -> list[list[str]]:
    """Cycles de dépendances entre packages (FR-008)."""
    return find_cycles(package_dependencies(graph))
