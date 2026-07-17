"""T005 — Tests du modèle IR : construction, invariants, JSON canonique."""

from __future__ import annotations

import json

import pytest

from codeatlas.ir.model import (
    Certainty,
    CodeGraph,
    Edge,
    EdgeKind,
    IRError,
    Location,
    Node,
    NodeKind,
    SubProject,
)
from codeatlas.ir.serialize import to_json


def make_node(node_id: str, kind: NodeKind = NodeKind.CLASS) -> Node:
    return Node(
        id=node_id,
        kind=kind,
        name=node_id.rsplit(".", 1)[-1],
        subproject="main",
        location=Location(file="pkg/mod.py", line=1),
    )


def make_graph(node_ids: list[str]) -> CodeGraph:
    graph = CodeGraph(root=".")
    graph.add_subproject(SubProject(id="main", language="python", root="."))
    for node_id in node_ids:
        graph.add_node(make_node(node_id))
    return graph


class TestInvariants:
    def test_duplicate_node_id_rejected(self) -> None:
        graph = make_graph(["main/pkg.A"])
        with pytest.raises(IRError, match=r"pkg\.A"):
            graph.add_node(make_node("main/pkg.A"))

    def test_edge_requires_existing_endpoints(self) -> None:
        graph = make_graph(["main/pkg.A"])
        with pytest.raises(IRError, match="inconnu"):
            edge = Edge(source="main/pkg.A", target="main/pkg.Missing", kind=EdgeKind.INHERITS)
            graph.add_edge(edge)

    def test_duplicate_edge_is_deduplicated(self) -> None:
        graph = make_graph(["main/pkg.A", "main/pkg.B"])
        edge = Edge(source="main/pkg.B", target="main/pkg.A", kind=EdgeKind.INHERITS)
        graph.add_edge(edge)
        graph.add_edge(edge)
        assert len(graph.edges) == 1

    def test_service_dep_links_subprojects(self) -> None:
        graph = CodeGraph(root=".")
        graph.add_subproject(SubProject(id="front", language="typescript", root="front"))
        graph.add_subproject(SubProject(id="back", language="python", root="back"))
        graph.add_edge(Edge(source="front", target="back", kind=EdgeKind.SERVICE_DEP))
        assert len(graph.edges) == 1

    def test_default_certainty_is_certain(self) -> None:
        edge = Edge(source="a", target="b", kind=EdgeKind.CALLS)
        assert edge.certainty is Certainty.CERTAIN


class TestDeterminism:
    def test_nodes_iterate_sorted_regardless_of_insertion_order(self) -> None:
        ids = ["main/pkg.Zeta", "main/pkg.Alpha", "main/pkg.Mid"]
        graph = make_graph(ids)
        assert [n.id for n in graph.iter_nodes()] == sorted(ids)

    def test_edges_sorted_regardless_of_insertion_order(self) -> None:
        graph = make_graph(["main/pkg.A", "main/pkg.B", "main/pkg.C"])
        graph.add_edge(Edge(source="main/pkg.C", target="main/pkg.A", kind=EdgeKind.ASSOCIATES))
        graph.add_edge(Edge(source="main/pkg.B", target="main/pkg.A", kind=EdgeKind.INHERITS))
        assert [(e.source, e.target) for e in graph.edges] == [
            ("main/pkg.B", "main/pkg.A"),
            ("main/pkg.C", "main/pkg.A"),
        ]


class TestCanonicalJson:
    def test_same_content_different_insertion_order_same_json(self) -> None:
        graph_a = make_graph(["main/pkg.A", "main/pkg.B"])
        graph_b = make_graph(["main/pkg.B", "main/pkg.A"])
        for graph in (graph_a, graph_b):
            graph.add_edge(Edge(source="main/pkg.B", target="main/pkg.A", kind=EdgeKind.INHERITS))
        assert to_json(graph_a) == to_json(graph_b)

    def test_json_shape(self) -> None:
        graph = make_graph(["main/pkg.A"])
        payload = json.loads(to_json(graph))
        assert payload["ir_version"] == 1
        assert payload["root"] == "."
        assert [n["id"] for n in payload["nodes"]] == ["main/pkg.A"]

    def test_json_omits_empty_fields_and_ends_with_newline(self) -> None:
        graph = make_graph(["main/pkg.A"])
        text = to_json(graph)
        assert text.endswith("\n")
        node = json.loads(text)["nodes"][0]
        assert "doc" not in node
        assert "complexity" not in node

    def test_json_contains_no_absolute_paths(self) -> None:
        graph = make_graph(["main/pkg.A"])
        assert "/home/" not in to_json(graph)
