"""Détection de design patterns par signatures structurelles sur l'IR (FR-013, R7).

Cinq patterns v1 : singleton, factory, observer, adapter, decorator. Chaque
détection porte des indices traçables ; en cas de doute, on ne détecte PAS
(les contre-exemples du corpus font foi — SC-008).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from codeatlas.ir.model import CodeGraph, EdgeKind, Node, NodeKind

_FACTORY_METHOD = re.compile(r"^(create|build|make)(_|[A-Z]|$)")
_SUBSCRIBE_NAMES = {"subscribe", "attach", "register_observer", "add_listener", "add_observer"}
_NOTIFY_NAMES = {"notify", "publish", "emit", "dispatch"}
_OBSERVER_ATTRS = {"observers", "listeners", "subscribers", "handlers"}
_INSTANCE_METHODS = {"instance", "get_instance", "getinstance", "shared"}


@dataclass(frozen=True, slots=True)
class PatternDetection:
    pattern: str
    class_id: str
    evidence: tuple[str, ...]
    confidence: str  # "high" | "medium"


class _ClassView:
    """Vue pratique d'une classe de l'IR pour les heuristiques."""

    def __init__(self, graph: CodeGraph, node: Node) -> None:
        self.graph = graph
        self.node = node
        prefix = f"{node.id}."
        self.methods: dict[str, Node] = {}
        self.attributes: dict[str, Node] = {}
        for member in graph.iter_nodes():
            if not member.id.startswith(prefix) or "." in member.id.removeprefix(prefix):
                continue
            if member.kind is NodeKind.METHOD:
                self.methods[member.name] = member
            elif member.kind is NodeKind.ATTRIBUTE:
                self.attributes[member.name] = member

        self.inherits: list[str] = []
        self.composes: list[str] = []
        self.calls_out: set[str] = set()
        for edge in graph.edges:
            if edge.kind in (EdgeKind.INHERITS, EdgeKind.IMPLEMENTS) and edge.source == node.id:
                self.inherits.append(edge.target)
            elif (
                edge.kind in (EdgeKind.COMPOSES, EdgeKind.AGGREGATES)
                and edge.source == node.id
            ):
                self.composes.append(edge.target)
            elif edge.kind is EdgeKind.CALLS and edge.source.startswith(prefix):
                self.calls_out.add(edge.target)

    def return_class(self, method: Node) -> str | None:
        """Classe analysée retournée par une méthode, d'après sa signature."""
        _, _, returns = method.signature.partition(" -> ")
        short = returns.strip().strip('"').strip("'")
        if not short:
            return None
        for other in self.graph.iter_nodes():
            if (
                other.kind in (NodeKind.CLASS, NodeKind.INTERFACE)
                and other.name == short.split("[")[0].split(" ")[0]
            ):
                return other.id
        return None


def _detect_singleton(view: _ClassView) -> PatternDetection | None:
    has_instance_attr = any(a in view.attributes for a in ("_instance", "_INSTANCE"))
    accessor = next((m for m in view.methods if m.lower() in _INSTANCE_METHODS), None)
    if has_instance_attr and accessor is not None:
        return PatternDetection(
            pattern="singleton",
            class_id=view.node.id,
            evidence=(
                "attribut de classe `_instance`",
                f"méthode d'accès `{accessor}`",
            ),
            confidence="high",
        )
    return None


def _detect_factory(view: _ClassView) -> PatternDetection | None:
    for name, method in sorted(view.methods.items()):
        if not _FACTORY_METHOD.match(name):
            continue
        produced = view.return_class(method)
        if produced is not None:
            return PatternDetection(
                pattern="factory",
                class_id=view.node.id,
                evidence=(
                    f"méthode `{name}` retourne `{produced.rsplit('.', 1)[-1]}`",
                ),
                confidence="high" if view.node.name.endswith("Factory") else "medium",
            )
    return None


def _detect_observer(view: _ClassView) -> PatternDetection | None:
    subscribe = next((m for m in view.methods if m.lower() in _SUBSCRIBE_NAMES), None)
    notify = next((m for m in view.methods if m.lower() in _NOTIFY_NAMES), None)
    registry = next((a for a in view.attributes if a.lower() in _OBSERVER_ATTRS), None)
    if subscribe and notify and registry:
        return PatternDetection(
            pattern="observer",
            class_id=view.node.id,
            evidence=(
                f"méthode d'abonnement `{subscribe}`",
                f"méthode de diffusion `{notify}`",
                f"registre d'abonnés `{registry}`",
            ),
            confidence="high",
        )
    return None


def _detect_decorator(view: _ClassView) -> PatternDetection | None:
    wrapped = sorted(set(view.inherits) & set(view.composes))
    if wrapped:
        target = wrapped[0].rsplit(".", 1)[-1]
        return PatternDetection(
            pattern="decorator",
            class_id=view.node.id,
            evidence=(
                f"hérite de `{target}`",
                f"enveloppe une instance de `{target}`",
            ),
            confidence="high",
        )
    return None


def _detect_adapter(view: _ClassView, graph: CodeGraph) -> PatternDetection | None:
    implemented = [
        t
        for t in view.inherits
        if (node := graph.get_node(t)) is not None and node.kind is NodeKind.INTERFACE
    ]
    delegates = [
        t
        for t in view.composes
        if t not in view.inherits
        and any(call.startswith(f"{t}.") for call in view.calls_out)
    ]
    if implemented and delegates:
        port = implemented[0].rsplit(".", 1)[-1]
        client = delegates[0].rsplit(".", 1)[-1]
        return PatternDetection(
            pattern="adapter",
            class_id=view.node.id,
            evidence=(
                f"implémente l'interface `{port}`",
                f"délègue à `{client}`",
            ),
            confidence="high",
        )
    return None


def detect_patterns(graph: CodeGraph) -> tuple[PatternDetection, ...]:
    """Détections triées par classe — au plus un pattern par classe (le plus sûr)."""
    detections: list[PatternDetection] = []
    for node in graph.iter_nodes(NodeKind.CLASS):
        view = _ClassView(graph, node)
        for detector in (_detect_singleton, _detect_observer, _detect_decorator):
            found = detector(view)
            if found is not None:
                detections.append(found)
                break
        else:
            found = _detect_adapter(view, graph) or _detect_factory(view)
            if found is not None:
                detections.append(found)
    return tuple(sorted(detections, key=lambda d: d.class_id))
