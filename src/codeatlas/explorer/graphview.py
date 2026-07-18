"""Vue d'architecture multi-niveaux (US1) — dérivée exclusivement de l'IR (FR-020).

Trois niveaux de dépliage : sous-projet → package → module. Les positions des
modules viennent du layout déterministe ; celles des conteneurs sont le barycentre
entier de leurs enfants. Les arêtes émises ne relient que des nœuds de même niveau :
imports entre modules (agrégés, avec certitude) et liens de services entre
sous-projets.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from codeatlas.config import Config
from codeatlas.explorer.layout import layered_positions
from codeatlas.graph.algorithms import module_package
from codeatlas.insights.architecture import compute_architecture
from codeatlas.insights.metrics import compute_metrics
from codeatlas.ir.model import CodeGraph, EdgeKind, NodeKind

LEVELS = ["subproject", "package", "module"]


def _qualname(node_id: str) -> str:
    return node_id.split("/", 1)[-1]


def _package_id(module_id: str) -> str:
    sub, qualname = module_id.split("/", 1) if "/" in module_id else ("", module_id)
    return f"pkg:{sub}/{module_package(qualname)}"


def _mean(values: list[int]) -> int:
    return round(sum(values) / len(values)) if values else 0


def _owning_subproject(graph: CodeGraph, path: str) -> str:
    """Sous-projet propriétaire d'un chemin (racine correspondante la plus profonde)."""
    best_id, best_len = "", -1
    for sub in graph.subprojects:
        if sub.root in (".", "") or path == sub.root or path.startswith(f"{sub.root}/"):
            depth = 0 if sub.root in (".", "") else len(sub.root)
            if depth > best_len:
                best_id, best_len = sub.id, depth
    return best_id


def build_graph_view(
    graph: CodeGraph, config: Config, page_for: Callable[[str], str]
) -> dict[str, Any]:
    """Données de la vue explorable : nœuds des trois niveaux, arêtes, positions."""
    modules = list(graph.iter_nodes(NodeKind.MODULE))
    module_ids = {m.id for m in modules}
    languages = {sub.id: sub.language for sub in graph.subprojects}

    layer_of_package: dict[str, str] = {}
    for layer in compute_architecture(graph).layers:
        for package in layer.packages:
            layer_of_package[package] = layer.name

    health = {row.module_id: row for row in compute_metrics(graph, config).modules}

    import_edges = [
        (e.source, e.target)
        for e in graph.edges_of_kind(EdgeKind.IMPORTS)
        if e.source in module_ids and e.target in module_ids and e.source != e.target
    ]
    positions = layered_positions(module_ids, import_edges)

    degraded_subs = {_owning_subproject(graph, s.path) for s in graph.skipped}

    nodes: list[dict[str, Any]] = []
    children: dict[str, list[str]] = {}
    for module in modules:
        package_id = _package_id(module.id)
        children.setdefault(package_id, []).append(module.id)
        row = health.get(module.id)
        nodes.append(
            {
                "id": module.id,
                "label": module.name,
                "level": "module",
                "parent": package_id,
                "language": languages.get(module.subproject, ""),
                "layer": layer_of_package.get(module_package(_qualname(module.id)), ""),
                "subproject": module.subproject,
                "metrics": {
                    "loc": module.loc,
                    "complexity": row.max_complexity if row else 0,
                    "doc_coverage": row.doc_coverage if row else 100,
                    "fan_in": row.fan_in if row else 0,
                    "fan_out": row.fan_out if row else 0,
                },
                "pos": {"x": positions[module.id][0], "y": positions[module.id][1]},
                "page": page_for(module.id),
                "degraded": False,
            }
        )

    for package_id in sorted(children):
        member_ids = children[package_id]
        owner_sub = package_id.removeprefix("pkg:").split("/", 1)[0]
        qualname = package_id.split("/", 1)[1]
        nodes.append(
            {
                "id": package_id,
                "label": qualname.rsplit(".", 1)[-1],
                "level": "package",
                "parent": f"sub:{owner_sub}",
                "language": languages.get(owner_sub, ""),
                "layer": layer_of_package.get(qualname, ""),
                "subproject": owner_sub,
                "metrics": {
                    "loc": sum(m.loc for m in modules if m.id in set(member_ids)),
                    "modules": len(member_ids),
                },
                "pos": {
                    "x": _mean([positions[m][0] for m in member_ids]),
                    "y": _mean([positions[m][1] for m in member_ids]),
                },
                "page": "",
                "degraded": False,
            }
        )

    for sub in graph.subprojects:
        member_modules = [m for m in modules if m.subproject == sub.id]
        xs = [positions[m.id][0] for m in member_modules]
        ys = [positions[m.id][1] for m in member_modules]
        nodes.append(
            {
                "id": f"sub:{sub.id}",
                "label": sub.id,
                "level": "subproject",
                "parent": None,
                "language": sub.language,
                "layer": "",
                "subproject": sub.id,
                "metrics": {
                    "loc": sum(m.loc for m in member_modules),
                    "modules": len(member_modules),
                },
                "pos": {"x": _mean(xs), "y": _mean(ys)},
                "page": "",
                "degraded": sub.id in degraded_subs,
            }
        )

    aggregated: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in graph.edges_of_kind(EdgeKind.IMPORTS):
        if edge.source not in module_ids or edge.target not in module_ids:
            continue
        if edge.source == edge.target:
            continue
        entry = aggregated.setdefault(
            (edge.source, edge.target),
            {"source": edge.source, "target": edge.target, "kind": "import",
             "certain": True, "weight": 0},
        )
        entry["weight"] += 1
        if edge.certainty.value != "certain":
            entry["certain"] = False
    edges = [aggregated[key] for key in sorted(aggregated)]
    for edge in graph.edges_of_kind(EdgeKind.SERVICE_DEP):
        edges.append(
            {
                "source": f"sub:{edge.source}",
                "target": f"sub:{edge.target}",
                "kind": "service",
                "certain": edge.certainty.value == "certain",
                "weight": 1,
            }
        )

    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: (e["source"], e["target"], e["kind"]))
    return {"levels": list(LEVELS), "nodes": nodes, "edges": edges}
