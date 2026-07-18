"""T005 — Vue d'architecture multi-niveaux construite depuis l'IR (US1, FR-001/002/020)."""

from __future__ import annotations

from codeatlas.config import Config
from codeatlas.explorer.graphview import build_graph_view
from codeatlas.ir.model import (
    Certainty,
    CodeGraph,
    Edge,
    EdgeKind,
    Location,
    Node,
    NodeKind,
    SkippedFile,
    SubProject,
)


def _page_for(module_id: str) -> str:
    return f"modules/{module_id.split('/', 1)[-1]}.html"


def _module(sub: str, qualname: str, file: str, loc: int = 10) -> Node:
    return Node(
        id=f"{sub}/{qualname}",
        kind=NodeKind.MODULE,
        name=qualname.rsplit(".", 1)[-1],
        subproject=sub,
        location=Location(file=file, line=1),
        loc=loc,
    )


def _graph() -> CodeGraph:
    graph = CodeGraph(root="demo")
    graph.add_subproject(SubProject(id="api", language="python", root="api"))
    graph.add_subproject(SubProject(id="lib", language="javascript", root="lib"))
    graph.add_node(_module("api", "app.api.routes", "api/app/api/routes.py"))
    graph.add_node(_module("api", "app.domain.orders", "api/app/domain/orders.py"))
    graph.add_node(_module("lib", "widgets.button", "lib/widgets/button.js"))
    graph.add_edge(
        Edge(source="api/app.api.routes", target="api/app.domain.orders", kind=EdgeKind.IMPORTS)
    )
    graph.add_edge(
        Edge(
            source="api/app.api.routes",
            target="api/app.domain.orders",
            kind=EdgeKind.IMPORTS,
            certainty=Certainty.INFERRED,
        )
    )
    graph.add_edge(Edge(source="api", target="lib", kind=EdgeKind.SERVICE_DEP))
    graph.add_skipped(SkippedFile(path="lib/broken.js", reason="syntax-error"))
    return graph


def test_levels_and_containment() -> None:
    view = build_graph_view(_graph(), Config(), _page_for)
    assert view["levels"] == ["subproject", "package", "module"]
    by_id = {n["id"]: n for n in view["nodes"]}
    module = by_id["api/app.api.routes"]
    assert module["level"] == "module"
    assert module["parent"] == "pkg:api/app.api"
    assert by_id["pkg:api/app.api"]["parent"] == "sub:api"
    assert by_id["sub:api"]["parent"] is None


def test_nodes_carry_filter_attributes_and_pages() -> None:
    view = build_graph_view(_graph(), Config(), _page_for)
    by_id = {n["id"]: n for n in view["nodes"]}
    module = by_id["api/app.api.routes"]
    assert module["language"] == "python"
    assert module["subproject"] == "api"
    assert module["layer"] == "api"  # convention de nommage (insights.architecture)
    assert module["page"] == "modules/app.api.routes.html"
    assert by_id["api/app.domain.orders"]["layer"] == "domain"
    assert by_id["lib/widgets.button"]["language"] == "javascript"


def test_module_metrics_and_positions_are_integers() -> None:
    view = build_graph_view(_graph(), Config(), _page_for)
    for node in view["nodes"]:
        assert isinstance(node["pos"]["x"], int) and isinstance(node["pos"]["y"], int)
    module = next(n for n in view["nodes"] if n["id"] == "api/app.api.routes")
    assert module["metrics"]["loc"] == 10
    assert set(module["metrics"]) == {"loc", "complexity", "doc_coverage", "fan_in", "fan_out"}


def test_edges_are_aggregated_per_level_and_sorted() -> None:
    view = build_graph_view(_graph(), Config(), _page_for)
    imports = [e for e in view["edges"] if e["kind"] == "import"]
    assert imports == [
        {
            "source": "api/app.api.routes",
            "target": "api/app.domain.orders",
            "kind": "import",
            "certain": False,  # au moins un lien inféré → arête incertaine
            "weight": 2,
        }
    ]
    services = [e for e in view["edges"] if e["kind"] == "service"]
    assert services == [
        {"source": "sub:api", "target": "sub:lib", "kind": "service", "certain": True, "weight": 1}
    ]
    assert view["edges"] == sorted(
        view["edges"], key=lambda e: (e["source"], e["target"], e["kind"])
    )


def test_degraded_marks_subprojects_with_skipped_files() -> None:
    view = build_graph_view(_graph(), Config(), _page_for)
    by_id = {n["id"]: n for n in view["nodes"]}
    assert by_id["sub:lib"]["degraded"] is True
    assert by_id["sub:api"]["degraded"] is False
    assert by_id["api/app.api.routes"]["degraded"] is False


def test_deterministic_and_sorted_nodes() -> None:
    first = build_graph_view(_graph(), Config(), _page_for)
    second = build_graph_view(_graph(), Config(), _page_for)
    assert first == second
    ids = [n["id"] for n in first["nodes"]]
    assert ids == sorted(ids)
