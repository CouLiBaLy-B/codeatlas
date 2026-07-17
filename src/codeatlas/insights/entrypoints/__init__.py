"""Détection des points d'entrée (FR-009) — opère uniquement sur l'IR.

Chaque reconnaisseur lit les modifiers portés par les nœuds (décorateurs, garde
main) ; toute détection porte son indice (`evidence`).
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.ir.model import CodeGraph


@dataclass(frozen=True, slots=True)
class EntryPoint:
    node_id: str
    framework: str  # "python", "click", "web"…
    kind: str  # "main" | "cli" | "route"
    label: str
    evidence: str


def detect_entrypoints(graph: CodeGraph) -> list[EntryPoint]:
    """Tous les points d'entrée du graphe, triés (kind, node_id) — déterministe."""
    from codeatlas.insights.entrypoints.java import recognize as recognize_java
    from codeatlas.insights.entrypoints.javascript import recognize as recognize_javascript
    from codeatlas.insights.entrypoints.python import recognize as recognize_python

    found = [
        *recognize_python(graph),
        *recognize_javascript(graph),
        *recognize_java(graph),
    ]
    return sorted(found, key=lambda e: (e.kind, e.node_id, e.framework, e.label))
