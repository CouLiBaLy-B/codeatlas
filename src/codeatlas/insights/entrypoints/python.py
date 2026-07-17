"""Reconnaisseurs de points d'entrée Python : main, CLI (click/typer), routes web."""

from __future__ import annotations

import re
from collections.abc import Iterator

from codeatlas.insights.entrypoints import EntryPoint
from codeatlas.ir.model import CodeGraph, NodeKind

# @app.get("/x"), @router.post("/y"), @app.route("/z")… (fastapi, flask, sanic…)
_ROUTE = re.compile(
    r"^decorator:(?P<obj>\w+)\.(?P<verb>get|post|put|delete|patch|route)\(\s*['\"](?P<path>[^'\"]*)['\"]"
)
# @click.command(), @cli.command(), @app.command() (click, typer)
_COMMAND = re.compile(r"^decorator:(?P<obj>[\w.]+)\.command\(")


def recognize(graph: CodeGraph) -> Iterator[EntryPoint]:
    for module in graph.iter_nodes(NodeKind.MODULE):
        if "main_guard" in module.modifiers:
            qualname = module.id.split("/", 1)[-1]
            yield EntryPoint(
                node_id=module.id,
                framework="python",
                kind="main",
                label=f"python -m {qualname}",
                evidence='if __name__ == "__main__"',
            )

    for kind in (NodeKind.FUNCTION, NodeKind.METHOD):
        for node in graph.iter_nodes(kind):
            for modifier in sorted(node.modifiers):
                route = _ROUTE.match(modifier)
                if route is not None:
                    verb = route.group("verb").upper()
                    label = f"{verb} {route.group('path')}" if verb != "ROUTE" else (
                        f"ROUTE {route.group('path')}"
                    )
                    yield EntryPoint(
                        node_id=node.id,
                        framework="web",
                        kind="route",
                        label=label,
                        evidence=f"@{modifier.removeprefix('decorator:')}",
                    )
                    continue
                command = _COMMAND.match(modifier)
                if command is not None:
                    prefix = command.group("obj").split(".")[0]
                    framework = "click" if prefix in ("click", "cli") else "cli-framework"
                    yield EntryPoint(
                        node_id=node.id,
                        framework=framework,
                        kind="cli",
                        label=node.id.split("/", 1)[-1],
                        evidence=f"@{modifier.removeprefix('decorator:')}",
                    )
