"""T006 — Golden du graphe d'un projet en layout src/ (feature 005)."""

from __future__ import annotations

from pathlib import Path

from codeatlas import api
from codeatlas.ir.serialize import to_json

CORPUS = Path(__file__).parents[2] / "examples" / "src-layout-demo"


def test_src_layout_graph_matches_golden(assert_golden) -> None:
    assert_golden("src_layout_graph.json", to_json(api.analyze(CORPUS)))


def test_src_layout_modules_are_importable_names() -> None:
    from codeatlas.ir.model import EdgeKind, NodeKind

    graph = api.analyze(CORPUS)
    module_ids = {n.id.split("/", 1)[-1] for n in graph.iter_nodes(NodeKind.MODULE)}
    # noms importables (sans le segment `src`)
    assert "mypkg.core" in module_ids
    assert "mypkg.models.order" in module_ids
    assert not any(m.startswith("src.") for m in module_ids)
    # les imports internes se résolvent en arêtes
    assert len(graph.edges_of_kind(EdgeKind.IMPORTS)) >= 4
