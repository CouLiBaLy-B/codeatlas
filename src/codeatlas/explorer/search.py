"""Index de recherche de symboles (US2) — précalculé, trié, jamais d'invention.

Chaque entrée vient du graphe de code (FR-008) ; le classement de pertinence est
fait côté client (préfixe exact > préfixe > sous-chaîne), l'index lui-même reste
canonique : tri (name, qualname).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from codeatlas.config import Config
from codeatlas.ir.model import CodeGraph, Node, NodeKind, Visibility

_INDEXED_KINDS = (
    NodeKind.MODULE,
    NodeKind.CLASS,
    NodeKind.INTERFACE,
    NodeKind.ENUM,
    NodeKind.FUNCTION,
    NodeKind.METHOD,
)


def _qualname(node_id: str) -> str:
    return node_id.split("/", 1)[-1]


def _anchor(name: str) -> str:
    """Ancre d'un titre `### \\`Name\\`` telle que slugifiée par MkDocs."""
    return name.lower()


def build_search_index(
    graph: CodeGraph, config: Config, page_for: Callable[[str], str]
) -> list[dict[str, Any]]:
    """Entrées de recherche pour modules, types, fonctions et méthodes visibles."""
    modules = list(graph.iter_nodes(NodeKind.MODULE))
    by_length = sorted(modules, key=lambda m: -len(m.id))

    def _owning_module(node: Node) -> Node | None:
        for module in by_length:
            if node.id.startswith(f"{module.id}."):
                return module
        return None

    entries: list[dict[str, Any]] = []
    for node in graph.iter_nodes():
        if node.kind not in _INDEXED_KINDS:
            continue
        if not config.analysis.include_private and node.visibility is Visibility.PRIVATE:
            continue
        owner: Node | None = node if node.kind is NodeKind.MODULE else _owning_module(node)
        if owner is None:
            continue  # symbole orphelin : jamais inventé de cible
        module = owner
        page = page_for(module.id)
        if node.kind in (NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM, NodeKind.FUNCTION):
            page = f"{page}#{_anchor(node.name)}"  # les fiches ont un titre par symbole
        elif node.kind is NodeKind.METHOD:
            owner_class = _qualname(node.id).rsplit(".", 2)[-2]
            page = f"{page}#{_anchor(owner_class)}"
        entries.append(
            {
                "name": node.name,
                "qualname": _qualname(node.id),
                "kind": node.kind.value,
                "signature": node.signature,
                "module": _qualname(module.id),
                "language": next(
                    (s.language for s in graph.subprojects if s.id == node.subproject), ""
                ),
                "page": page,
            }
        )
    entries.sort(key=lambda e: (e["name"], e["qualname"]))
    return entries
