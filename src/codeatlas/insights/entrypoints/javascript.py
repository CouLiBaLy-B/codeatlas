"""Reconnaisseur de points d'entrée JavaScript/TypeScript : routes express."""

from __future__ import annotations

from collections.abc import Iterator

from codeatlas.insights.entrypoints import EntryPoint
from codeatlas.ir.model import CodeGraph, NodeKind


def recognize(graph: CodeGraph) -> Iterator[EntryPoint]:
    for module in graph.iter_nodes(NodeKind.MODULE):
        for modifier in sorted(module.modifiers):
            if modifier.startswith("route:"):
                yield EntryPoint(
                    node_id=module.id,
                    framework="web",
                    kind="route",
                    label=modifier.removeprefix("route:"),
                    evidence="enregistrement de route au niveau module (express-like)",
                )
