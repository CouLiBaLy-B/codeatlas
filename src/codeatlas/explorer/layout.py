"""Layout hiérarchique déterministe (R2) — calculé au build, jamais côté client.

Sugiyama simplifié : rang topologique sur la condensation (les cycles partagent un
rang), puis réduction des croisements par tri barycentrique à nombre d'itérations
FIXE. Aucune source d'aléa, coordonnées entières : reproductible octet pour octet.
"""

from __future__ import annotations

from collections.abc import Iterable

import networkx as nx

X_GAP = 240  # écart horizontal entre rangs (px)
Y_GAP = 96  # écart vertical entre nœuds d'un même rang (px)
_SWEEPS = 4  # passes barycentriques — fixe, pour le déterminisme


def _ranks(nodes: list[str], edges: list[tuple[str, str]]) -> dict[str, int]:
    graph: nx.DiGraph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    condensed = nx.condensation(graph)
    rank_of_scc: dict[int, int] = {}
    for scc in nx.topological_sort(condensed):
        preds = list(condensed.predecessors(scc))
        rank_of_scc[scc] = max((rank_of_scc[p] + 1 for p in preds), default=0)
    mapping = condensed.graph["mapping"]  # nœud → id de sa composante
    return {node: rank_of_scc[mapping[node]] for node in nodes}


def layered_positions(
    nodes: Iterable[str], edges: Iterable[tuple[str, str]]
) -> dict[str, tuple[int, int]]:
    """Positions (x, y) entières de chaque nœud ; x croît dans le sens des arêtes."""
    node_list = sorted(set(nodes))
    edge_list = sorted({(s, t) for s, t in edges if s != t})
    if not node_list:
        return {}
    ranks = _ranks(node_list, edge_list)

    columns: dict[int, list[str]] = {}
    for node in node_list:  # ordre initial lexicographique (déterministe)
        columns.setdefault(ranks[node], []).append(node)

    neighbors: dict[str, list[str]] = {n: [] for n in node_list}
    for source, target in edge_list:
        neighbors[source].append(target)
        neighbors[target].append(source)

    order: dict[str, int] = {}
    for column in columns.values():
        for index, node in enumerate(column):
            order[node] = index
    for _ in range(_SWEEPS):
        for rank in sorted(columns):
            column = columns[rank]
            # barycentre des voisins (rangs adjacents) ; le nom départage les égalités
            column.sort(
                key=lambda n: (
                    (
                        sum(order[v] for v in neighbors[n]) / len(neighbors[n])
                        if neighbors[n]
                        else order[n]
                    ),
                    n,
                )
            )
            for index, node in enumerate(column):
                order[node] = index

    positions: dict[str, tuple[int, int]] = {}
    for rank, column in columns.items():
        offset = (len(column) - 1) / 2
        for index, node in enumerate(column):
            positions[node] = (rank * X_GAP, round((index - offset) * Y_GAP))
    return positions
