"""Renderer Mermaid du graphe de dépendances entre packages, cycles surlignés."""

from __future__ import annotations

from codeatlas.graph.algorithms import package_cycles, package_dependencies
from codeatlas.ir.model import CodeGraph


def render_package_deps(graph: CodeGraph) -> str:
    """`graph LR` des dépendances de packages ; les arêtes des cycles sont en rouge."""
    pairs = package_dependencies(graph)
    cycles = package_cycles(graph)
    cycle_members: list[set[str]] = [set(cycle) for cycle in cycles]

    packages = sorted({name for pair in pairs for name in pair})
    alias = {name: f"p{index}" for index, name in enumerate(packages)}

    lines = ["graph LR"]
    for name in packages:
        lines.append(f'    {alias[name]}["{name}"]')

    cycle_edge_indexes: list[int] = []
    for index, (source, target) in enumerate(pairs):
        lines.append(f"    {alias[source]} --> {alias[target]}")
        if any(source in members and target in members for members in cycle_members):
            cycle_edge_indexes.append(index)

    if cycle_edge_indexes:
        cycle_nodes = sorted({name for members in cycle_members for name in members})
        lines.append("    classDef cycle stroke:#d33,stroke-width:2px")
        lines.append(f"    class {','.join(alias[n] for n in cycle_nodes)} cycle")
        joined = ",".join(str(i) for i in cycle_edge_indexes)
        lines.append(f"    linkStyle {joined} stroke:#d33,stroke-width:2px")
    return "\n".join(lines) + "\n"
