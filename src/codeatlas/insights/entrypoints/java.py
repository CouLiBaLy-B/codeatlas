"""Reconnaisseurs de points d'entrée Java : main statique, routes Spring."""

from __future__ import annotations

import re
from collections.abc import Iterator

from codeatlas.insights.entrypoints import EntryPoint
from codeatlas.ir.model import CodeGraph, NodeKind

_MAPPING = re.compile(
    r"^decorator:(?P<verb>Get|Post|Put|Delete|Patch|Request)Mapping"
    r"(?:\(\s*\"(?P<path>[^\"]*)\")?"
)


def recognize(graph: CodeGraph) -> Iterator[EntryPoint]:
    for node in graph.iter_nodes(NodeKind.METHOD):
        if node.name == "main" and "static" in node.modifiers:
            yield EntryPoint(
                node_id=node.id,
                framework="java",
                kind="main",
                label=node.id.split("/", 1)[-1],
                evidence="public static void main(String[] args)",
            )
            continue
        for modifier in sorted(node.modifiers):
            match = _MAPPING.match(modifier)
            if match is not None:
                verb = match.group("verb").upper()
                path = match.group("path") or "/"
                yield EntryPoint(
                    node_id=node.id,
                    framework="spring",
                    kind="route",
                    label=f"{'ROUTE' if verb == 'REQUEST' else verb} {path}",
                    evidence=f"@{modifier.removeprefix('decorator:')}",
                )
