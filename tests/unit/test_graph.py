"""T008 — Tests des algorithmes de graphe : cycles, atteignabilité, déterminisme."""

from __future__ import annotations

from codeatlas.graph.algorithms import find_cycles, package_dependencies, reachable_from
from codeatlas.ir.model import CodeGraph, Edge, EdgeKind, Location, Node, NodeKind, SubProject


class TestFindCycles:
    def test_no_cycle(self) -> None:
        assert find_cycles([("a", "b"), ("b", "c")]) == []

    def test_two_node_cycle(self) -> None:
        assert find_cycles([("a", "b"), ("b", "a"), ("b", "c")]) == [["a", "b"]]

    def test_self_loop_is_a_cycle(self) -> None:
        assert find_cycles([("a", "a")]) == [["a"]]

    def test_cycles_are_deterministic_and_normalized(self) -> None:
        edges = [("z", "m"), ("m", "z"), ("b", "a"), ("a", "b")]
        result = find_cycles(edges)
        assert result == find_cycles(list(reversed(edges)))
        assert result == [["a", "b"], ["m", "z"]]


class TestReachableFrom:
    def test_reaches_transitively(self) -> None:
        edges = [("main", "svc"), ("svc", "db"), ("orphan", "other")]
        assert reachable_from(edges, ["main"]) == frozenset({"main", "svc", "db"})

    def test_unknown_source_is_just_itself(self) -> None:
        assert reachable_from([("a", "b")], ["zz"]) == frozenset({"zz"})


class TestPackageDependencies:
    def _graph(self) -> CodeGraph:
        graph = CodeGraph(root=".")
        graph.add_subproject(SubProject(id="main", language="python", root="."))
        for module_id, file in [
            ("main/app.services.catalog", "app/services/catalog.py"),
            ("main/app.models.product", "app/models/product.py"),
            ("main/app.services.orders", "app/services/orders.py"),
        ]:
            graph.add_node(
                Node(
                    id=module_id,
                    kind=NodeKind.MODULE,
                    name=module_id.rsplit(".", 1)[-1],
                    subproject="main",
                    location=Location(file=file, line=1),
                )
            )
        graph.add_edge(
            Edge(
                source="main/app.services.catalog",
                target="main/app.models.product",
                kind=EdgeKind.IMPORTS,
            )
        )
        graph.add_edge(
            Edge(
                source="main/app.services.orders",
                target="main/app.services.catalog",
                kind=EdgeKind.IMPORTS,
            )
        )
        return graph

    def test_module_imports_aggregate_to_packages_without_self_deps(self) -> None:
        deps = package_dependencies(self._graph())
        assert deps == [("app.services", "app.models")]
