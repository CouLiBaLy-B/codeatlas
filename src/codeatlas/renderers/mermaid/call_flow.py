"""Renderer Mermaid `flowchart` des flux d'appels — appelants ET appelés (FR-010).

Les arêtes `inferred` sont rendues en pointillés (`-.->`), jamais confondues avec
les appels sûrs (FR-009).
"""

from __future__ import annotations

from collections import deque

from codeatlas.ir.model import Certainty, CodeGraph, Edge, EdgeKind


def _bfs(
    adjacency: dict[str, list[Edge]],
    root: str,
    depth: int,
    reverse: bool,
) -> set[tuple[str, str, str]]:
    """Arêtes traversées depuis `root` jusqu'à `depth` niveaux."""
    traversed: set[tuple[str, str, str]] = set()
    queue: deque[tuple[str, int]] = deque([(root, 0)])
    seen = {root}
    while queue:
        node, level = queue.popleft()
        if level >= depth:
            continue
        for edge in adjacency.get(node, []):
            neighbor = edge.source if reverse else edge.target
            traversed.add((edge.source, edge.target, edge.certainty.value))
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, level + 1))
    return traversed


def render_call_flow(graph: CodeGraph, root_id: str, depth: int) -> str:
    """Flux d'appels autour de `root_id` : appelés ET appelants jusqu'à `depth`."""
    forward: dict[str, list[Edge]] = {}
    backward: dict[str, list[Edge]] = {}
    for edge in graph.edges_of_kind(EdgeKind.CALLS):
        forward.setdefault(edge.source, []).append(edge)
        backward.setdefault(edge.target, []).append(edge)

    traversed = _bfs(forward, root_id, depth, reverse=False)
    traversed |= _bfs(backward, root_id, depth, reverse=True)

    included = {root_id} | {n for s, t, _ in traversed for n in (s, t)}
    label = {node_id: node_id.split("/", 1)[-1] for node_id in included}
    alias = {node_id: f"n{index}" for index, node_id in enumerate(sorted(included))}

    lines = ["flowchart TD"]
    for node_id in sorted(included):
        if node_id == root_id:
            lines.append(f'    {alias[node_id]}(["{label[node_id]}"])')
        else:
            lines.append(f'    {alias[node_id]}["{label[node_id]}"]')
    for source, target, certainty in sorted(traversed):
        arrow = "-.->" if certainty == Certainty.INFERRED.value else "-->"
        lines.append(f"    {alias[source]} {arrow} {alias[target]}")
    return "\n".join(lines) + "\n"
