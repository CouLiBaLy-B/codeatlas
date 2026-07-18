"""Outils du serveur MCP — fonctions pures sur le graphe de code (FR-004/005).

Chaque réponse provient exclusivement du graphe : liste vide ou erreur outillée
plutôt qu'invention ; résultats bornés ; certitude des liens toujours distinguée.
"""

from __future__ import annotations

from typing import Any

from codeatlas.config import Config
from codeatlas.ir.model import CodeGraph, EdgeKind, Node, NodeKind, Visibility

DEFAULT_LIMIT = 25

_SYMBOL_KINDS = (
    NodeKind.MODULE,
    NodeKind.CLASS,
    NodeKind.INTERFACE,
    NodeKind.ENUM,
    NodeKind.FUNCTION,
    NodeKind.METHOD,
)


def _qualname(node_id: str) -> str:
    return node_id.split("/", 1)[-1]


def _describe(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "kind": node.kind.value,
        "file": node.location.file,
        "line": node.location.line,
        "signature": node.signature,
        "doc": node.doc.summary if node.doc else "",
    }


def _find_candidates(graph: CodeGraph, query: str, kinds: tuple[NodeKind, ...]) -> list[Node]:
    exact: list[Node] = []
    suffix: list[Node] = []
    for node in graph.iter_nodes():
        if node.kind not in kinds:
            continue
        qualname = _qualname(node.id)
        if node.id == query or qualname == query:
            exact.append(node)
        elif qualname.endswith(f".{query}"):
            suffix.append(node)
    return exact if exact else suffix


def _resolve_unique(
    graph: CodeGraph, query: str, kinds: tuple[NodeKind, ...]
) -> tuple[Node | None, dict[str, Any] | None]:
    candidates = _find_candidates(graph, query, kinds)
    if not candidates:
        return None, {"error": f"symbole introuvable : {query}", "candidates": []}
    if len(candidates) > 1:
        return None, {
            "error": f"symbole ambigu : {query}",
            "candidates": [c.id for c in candidates],
        }
    return candidates[0], None


def search_symbol(graph: CodeGraph, query: str, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    """Correspondances exactes puis par suffixe puis par sous-chaîne — bornées."""
    matches: list[Node] = list(_find_candidates(graph, query, _SYMBOL_KINDS))
    seen = {node.id for node in matches}
    lowered = query.lower()
    for node in graph.iter_nodes():
        if node.kind in _SYMBOL_KINDS and node.id not in seen and lowered in node.name.lower():
            matches.append(node)
            seen.add(node.id)
    truncated = len(matches) > limit
    return {
        "matches": [_describe(node) for node in matches[:limit]],
        "truncated": truncated,
    }


def module_api(graph: CodeGraph, module: str) -> dict[str, Any]:
    """Surface publique d'un module : classes (avec méthodes) et fonctions."""
    node, error = _resolve_unique(graph, module, (NodeKind.MODULE,))
    if node is None:
        assert error is not None
        return error
    classes = []
    for kind in (NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM):
        for cls in graph.children_of(node.id, kind):
            if cls.visibility is Visibility.PRIVATE:
                continue
            classes.append(
                {
                    "name": cls.name,
                    "kind": cls.kind.value,
                    "doc": cls.doc.summary if cls.doc else "",
                    "methods": [
                        _describe(m)
                        for m in graph.children_of(cls.id, NodeKind.METHOD)
                        if m.visibility is not Visibility.PRIVATE
                    ],
                }
            )
    functions = [
        _describe(fn)
        for fn in graph.children_of(node.id, NodeKind.FUNCTION)
        if fn.visibility is not Visibility.PRIVATE
    ]
    return {
        "module": _qualname(node.id),
        "doc": node.doc.summary if node.doc else "",
        "classes": classes,
        "functions": functions,
    }


def _links(graph: CodeGraph, symbol: str, incoming: bool) -> dict[str, Any]:
    node, error = _resolve_unique(
        graph, symbol, (NodeKind.FUNCTION, NodeKind.METHOD, NodeKind.CLASS, NodeKind.MODULE)
    )
    if node is None:
        assert error is not None
        return error
    key = "callers" if incoming else "callees"
    links = []
    for edge in graph.edges_of_kind(EdgeKind.CALLS):
        if incoming and edge.target == node.id:
            links.append({"id": edge.source, "certainty": edge.certainty.value})
        elif not incoming and edge.source == node.id:
            links.append({"id": edge.target, "certainty": edge.certainty.value})
    return {"symbol": node.id, key: sorted(links, key=lambda item: item["id"])}


def callers(graph: CodeGraph, symbol: str) -> dict[str, Any]:
    """Qui appelle ce symbole (certitude distinguée)."""
    return _links(graph, symbol, incoming=True)


def callees(graph: CodeGraph, symbol: str) -> dict[str, Any]:
    """Ce que ce symbole appelle (certitude distinguée)."""
    return _links(graph, symbol, incoming=False)


def impact(graph: CodeGraph, target: str, depth: int = 3) -> dict[str, Any]:
    """Analyse d'impact (réutilise l'insight de la feature 003/US3)."""
    from codeatlas.insights.impact import compute_impact

    node, error = _resolve_unique(graph, target, _SYMBOL_KINDS)
    if node is None:
        assert error is not None
        return error
    report = compute_impact(graph, (node.id,), depth)
    return {
        "target": node.id,
        "levels": [
            {
                "depth": level.depth,
                "entries": [
                    {"id": e.id, "via": e.via, "certainty": e.certainty}
                    for e in level.entries
                ],
            }
            for level in report.levels
        ],
        "entrypoints_reached": list(report.entrypoints_reached),
    }


def dead_code(graph: CodeGraph) -> dict[str, Any]:
    """Candidats code mort avec confiance et raison."""
    from codeatlas.insights.deadcode import find_dead_code

    return {
        "candidates": [
            {"id": c.node_id, "confidence": c.confidence, "reason": c.reason}
            for c in find_dead_code(graph)
        ]
    }


def overview(graph: CodeGraph, config: Config) -> dict[str, Any]:
    """Vue d'ensemble : sous-projets, couches, points d'entrée, métriques."""
    from codeatlas.insights.architecture import compute_architecture
    from codeatlas.insights.entrypoints import detect_entrypoints
    from codeatlas.insights.metrics import compute_metrics

    health = compute_metrics(graph, config)
    architecture = compute_architecture(graph)
    return {
        "root": graph.root,
        "subprojects": [
            {"id": s.id, "language": s.language} for s in graph.subprojects
        ],
        "modules": sum(1 for _ in graph.iter_nodes(NodeKind.MODULE)),
        "symbols": len(graph.nodes),
        "doc_coverage": health.global_doc_coverage,
        "layers": [
            {"name": layer.name, "level": layer.level, "packages": list(layer.packages)}
            for layer in architecture.layers
        ],
        "entrypoints": [
            {"label": e.label, "kind": e.kind, "id": e.node_id}
            for e in detect_entrypoints(graph)
        ],
        "skipped": [{"path": s.path, "reason": s.reason} for s in graph.skipped],
    }
