"""Renderer Mermaid du graphe de dépendances inter-services (monorepo, FR-015)."""

from __future__ import annotations

from codeatlas.ir.model import CodeGraph, EdgeKind


def render_services(graph: CodeGraph) -> str:
    subprojects = graph.subprojects
    alias = {sub.id: f"s{index}" for index, sub in enumerate(subprojects)}
    lines = ["graph LR"]
    for sub in subprojects:
        lines.append(f'    {alias[sub.id]}["{sub.id} ({sub.language})"]')
    for edge in graph.edges_of_kind(EdgeKind.SERVICE_DEP):
        lines.append(f"    {alias[edge.source]} --> {alias[edge.target]}")
    return "\n".join(lines) + "\n"
