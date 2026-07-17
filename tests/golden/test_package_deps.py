"""T019 — Golden tests du diagramme de dépendances de packages avec cycles."""

from __future__ import annotations

from codeatlas.graph.algorithms import package_cycles
from codeatlas.renderers.mermaid.package_deps import render_package_deps

from .corpus import corpus_graph


def test_package_dependency_diagram(assert_golden) -> None:
    assert_golden("package_deps.mmd", render_package_deps(corpus_graph()))


def test_intentional_cycle_detected() -> None:
    assert package_cycles(corpus_graph()) == [["shopdemo.legacy", "shopdemo.services"]]


def test_cycle_edges_are_highlighted() -> None:
    diagram = render_package_deps(corpus_graph())
    assert "linkStyle" in diagram  # les arêtes du cycle sont stylées en rouge
    assert "stroke:#d33" in diagram
