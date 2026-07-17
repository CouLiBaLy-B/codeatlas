"""Renderer Mermaid de la vue architecture : couches en subgraphs, violations en rouge."""

from __future__ import annotations

from codeatlas.graph.algorithms import package_dependencies
from codeatlas.insights.architecture import ArchitectureReport
from codeatlas.ir.model import CodeGraph


def render_architecture(graph: CodeGraph, report: ArchitectureReport) -> str:
    assigned = {pkg for layer in report.layers for pkg in layer.packages}
    alias = {pkg: f"p{index}" for index, pkg in enumerate(sorted(assigned))}
    violating = {(v.source_package, v.target_package) for v in report.violations}

    lines = ["flowchart TD"]
    for layer in report.layers:  # déjà triées du haut vers le bas
        lines.append(f'    subgraph {layer.name}["{layer.name}"]')
        for pkg in layer.packages:
            lines.append(f'        {alias[pkg]}["{pkg}"]')
        lines.append("    end")

    violation_indexes: list[int] = []
    index = 0
    for source, target in package_dependencies(graph):
        if source not in assigned or target not in assigned:
            continue
        lines.append(f"    {alias[source]} --> {alias[target]}")
        if (source, target) in violating:
            violation_indexes.append(index)
        index += 1

    if violation_indexes:
        joined = ",".join(str(i) for i in violation_indexes)
        lines.append(f"    linkStyle {joined} stroke:#d33,stroke-width:2px")
    return "\n".join(lines) + "\n"
