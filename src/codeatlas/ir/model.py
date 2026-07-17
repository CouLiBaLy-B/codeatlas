"""Modèle de la représentation intermédiaire (IR) : le graphe de code unifié.

Contrat : specs/001-intelligent-doc-generator/contracts/ir-schema.md.
Ce module ne dépend d'AUCUN analyseur de langage (constitution, principe III).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum

IR_VERSION = 1


class IRError(Exception):
    """Violation d'un invariant du graphe de code."""


class NodeKind(StrEnum):
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    INTERFACE = "interface"
    ENUM = "enum"
    FUNCTION = "function"
    METHOD = "method"
    ATTRIBUTE = "attribute"


class EdgeKind(StrEnum):
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    COMPOSES = "composes"
    AGGREGATES = "aggregates"
    ASSOCIATES = "associates"
    IMPORTS = "imports"
    CALLS = "calls"
    REFERENCES = "references"
    SERVICE_DEP = "service_dep"


class Certainty(StrEnum):
    CERTAIN = "certain"
    INFERRED = "inferred"


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class DocFormat(StrEnum):
    DOCSTRING = "docstring"
    JSDOC = "jsdoc"
    JAVADOC = "javadoc"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Location:
    """Position d'un fait dans les sources — chemin POSIX relatif, jamais absolu."""

    file: str
    line: int


@dataclass(frozen=True, slots=True)
class DocInfo:
    raw: str
    summary: str
    format: DocFormat = DocFormat.DOCSTRING


@dataclass(frozen=True, slots=True)
class SubProject:
    id: str
    language: str
    root: str
    manifest: str = ""
    declared_deps: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkippedFile:
    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    kind: NodeKind
    name: str
    subproject: str
    location: Location
    visibility: Visibility = Visibility.PUBLIC
    signature: str = ""
    doc: DocInfo | None = None
    modifiers: frozenset[str] = frozenset()
    complexity: int | None = None
    loc: int = 0


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    kind: EdgeKind
    certainty: Certainty = Certainty.CERTAIN
    location: Location | None = None

    def key(self) -> tuple[str, str, str, str]:
        return (self.source, self.target, self.kind.value, self.certainty.value)


@dataclass
class CodeGraph:
    """Graphe de code d'un dépôt. Itération toujours en ordre trié (déterminisme)."""

    root: str
    _subprojects: dict[str, SubProject] = field(default_factory=dict)
    _nodes: dict[str, Node] = field(default_factory=dict)
    _edges: dict[tuple[str, str, str, str], Edge] = field(default_factory=dict)
    _skipped: list[SkippedFile] = field(default_factory=list)
    # caches invalidés à chaque ajout (performance : évite les tris répétés)
    _sorted_ids: tuple[str, ...] | None = field(default=None, repr=False)
    _sorted_edges: tuple[Edge, ...] | None = field(default=None, repr=False)
    _children_index: dict[str, tuple[str, ...]] | None = field(default=None, repr=False)
    _file_index: dict[str, tuple[str, ...]] | None = field(default=None, repr=False)

    # -- construction -------------------------------------------------------

    def add_subproject(self, subproject: SubProject) -> None:
        if subproject.id in self._subprojects:
            raise IRError(f"sous-projet dupliqué : {subproject.id!r}")
        self._subprojects[subproject.id] = subproject

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise IRError(f"nœud dupliqué : {node.id!r}")
        if node.subproject not in self._subprojects:
            raise IRError(f"sous-projet inconnu pour {node.id!r} : {node.subproject!r}")
        self._nodes[node.id] = node
        self._sorted_ids = None
        self._children_index = None
        self._file_index = None

    def add_edge(self, edge: Edge) -> None:
        if edge.kind is EdgeKind.SERVICE_DEP:
            universe = self._subprojects
        else:
            universe = self._nodes  # type: ignore[assignment]
        for endpoint in (edge.source, edge.target):
            if endpoint not in universe:
                raise IRError(f"extrémité d'arête inconnue : {endpoint!r} ({edge.kind.value})")
        self._edges.setdefault(edge.key(), edge)
        self._sorted_edges = None

    def add_skipped(self, skipped: SkippedFile) -> None:
        self._skipped.append(skipped)

    # -- lecture (toujours triée) -------------------------------------------

    @property
    def subprojects(self) -> tuple[SubProject, ...]:
        return tuple(self._subprojects[k] for k in sorted(self._subprojects))

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def iter_nodes(self, kind: NodeKind | None = None) -> Iterator[Node]:
        if self._sorted_ids is None:
            self._sorted_ids = tuple(sorted(self._nodes))
        for node_id in self._sorted_ids:
            node = self._nodes[node_id]
            if kind is None or node.kind is kind:
                yield node

    def children_of(self, parent_id: str, kind: NodeKind | None = None) -> list[Node]:
        """Enfants directs d'un nœud (ex. méthodes d'une classe), triés par id."""
        if self._children_index is None:
            index: dict[str, list[str]] = {}
            for node_id in sorted(self._nodes):
                if "." in node_id:
                    index.setdefault(node_id.rsplit(".", 1)[0], []).append(node_id)
            self._children_index = {k: tuple(v) for k, v in index.items()}
        children = [self._nodes[i] for i in self._children_index.get(parent_id, ())]
        if kind is not None:
            children = [n for n in children if n.kind is kind]
        return children

    def nodes_in_file(self, file: str) -> list[Node]:
        """Nœuds définis dans un fichier donné, triés par id."""
        if self._file_index is None:
            index: dict[str, list[str]] = {}
            for node_id in sorted(self._nodes):
                index.setdefault(self._nodes[node_id].location.file, []).append(node_id)
            self._file_index = {k: tuple(v) for k, v in index.items()}
        return [self._nodes[i] for i in self._file_index.get(file, ())]

    @property
    def edges(self) -> tuple[Edge, ...]:
        if self._sorted_edges is None:
            self._sorted_edges = tuple(self._edges[k] for k in sorted(self._edges))
        return self._sorted_edges

    def edges_of_kind(self, *kinds: EdgeKind) -> tuple[Edge, ...]:
        wanted = set(kinds)
        return tuple(e for e in self.edges if e.kind in wanted)

    @property
    def skipped(self) -> tuple[SkippedFile, ...]:
        return tuple(sorted(self._skipped, key=lambda s: s.path))
