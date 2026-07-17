"""Sérialisation JSON canonique de l'IR : clés triées, champs vides omis, fin `\\n`."""

from __future__ import annotations

import json
from typing import Any

from codeatlas.ir.model import IR_VERSION, CodeGraph, Edge, Node, SubProject


def _clean(mapping: dict[str, Any]) -> dict[str, Any]:
    """Retire les champs vides/None pour un JSON minimal et stable."""
    return {k: v for k, v in mapping.items() if v not in (None, "", [], {}, ())}


def _subproject_dict(subproject: SubProject) -> dict[str, Any]:
    return _clean(
        {
            "id": subproject.id,
            "language": subproject.language,
            "root": subproject.root,
            "manifest": subproject.manifest,
            "declared_deps": list(subproject.declared_deps),
        }
    )


def _node_dict(node: Node) -> dict[str, Any]:
    doc = None
    if node.doc is not None:
        doc = _clean(
            {"raw": node.doc.raw, "summary": node.doc.summary, "format": node.doc.format.value}
        )
    return _clean(
        {
            "id": node.id,
            "kind": node.kind.value,
            "name": node.name,
            "subproject": node.subproject,
            "file": node.location.file,
            "line": node.location.line,
            "visibility": node.visibility.value,
            "signature": node.signature,
            "doc": doc,
            "modifiers": sorted(node.modifiers),
            "complexity": node.complexity,
            "loc": node.loc or None,
        }
    )


def _edge_dict(edge: Edge) -> dict[str, Any]:
    payload = _clean(
        {
            "source": edge.source,
            "target": edge.target,
            "kind": edge.kind.value,
            "certainty": edge.certainty.value,
        }
    )
    if edge.location is not None:
        payload["file"] = edge.location.file
        payload["line"] = edge.location.line
    return payload


def to_json(graph: CodeGraph) -> str:
    """JSON canonique du graphe : déterministe octet pour octet."""
    payload = {
        "ir_version": IR_VERSION,
        "root": graph.root,
        "subprojects": [_subproject_dict(s) for s in graph.subprojects],
        "nodes": [_node_dict(n) for n in graph.iter_nodes()],
        "edges": [_edge_dict(e) for e in graph.edges],
        "skipped": [{"path": s.path, "reason": s.reason} for s in graph.skipped],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
