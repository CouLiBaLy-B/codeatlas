"""T023 — Tableau de bord explorable (US4) : lignes, treemap squarify, SVG."""

from __future__ import annotations

from codeatlas.config import Config
from codeatlas.explorer.dashboard import build_dashboard, render_treemap_svg, treemap_cells
from codeatlas.ir.model import CodeGraph, Location, Node, NodeKind, SkippedFile, SubProject


def _page_for(module_id: str) -> str:
    return f"modules/{module_id.split('/', 1)[-1]}.html"


def _graph() -> CodeGraph:
    graph = CodeGraph(root="demo")
    graph.add_subproject(SubProject(id="main", language="python", root="."))
    for name, loc in (("app.alpha", 120), ("app.beta", 40), ("app.gamma", 0)):
        graph.add_node(
            Node(
                id=f"main/{name}",
                kind=NodeKind.MODULE,
                name=name.rsplit(".", 1)[-1],
                subproject="main",
                location=Location(file=f"{name.replace('.', '/')}.py", line=1),
                loc=loc,
            )
        )
    graph.add_skipped(SkippedFile(path="app/broken.py", reason="syntax-error"))
    return graph


def test_rows_are_sorted_with_homogeneous_metrics() -> None:
    dashboard = build_dashboard(_graph(), Config(), _page_for)
    rows = dashboard["rows"]
    assert [r["id"] for r in rows] == sorted(r["id"] for r in rows)
    keys = {tuple(sorted(r["metrics"])) for r in rows}
    assert keys == {("complexity", "doc_coverage", "fan_in", "fan_out", "loc")}
    assert all(r["page"] for r in rows)


def test_warnings_are_exposed_with_reason() -> None:
    dashboard = build_dashboard(_graph(), Config(), _page_for)
    assert {"path": "app/broken.py", "reason": "syntax-error", "scope": "file"} in dashboard[
        "warnings"
    ]


def test_treemap_cells_partition_the_canvas() -> None:
    items = [("a", "A", "a.html", 6.0), ("b", "B", "b.html", 6.0), ("c", "C", "c.html", 4.0),
             ("d", "D", "d.html", 3.0), ("e", "E", "e.html", 2.0), ("f", "F", "f.html", 2.0),
             ("g", "G", "g.html", 1.0)]
    cells = treemap_cells(items, width=600, height=400)
    assert len(cells) == 7
    total = sum(c["w"] * c["h"] for c in cells)
    assert abs(total - 600 * 400) <= 600 * 400 * 0.02  # partition quasi exacte
    for cell in cells:
        assert isinstance(cell["x"], int) and isinstance(cell["w"], int)
        assert 0 <= cell["x"] <= 600 and 0 <= cell["y"] <= 400
        assert cell["x"] + cell["w"] <= 600 and cell["y"] + cell["h"] <= 400
        assert cell["w"] > 0 and cell["h"] > 0
    for first in cells:  # jamais deux cellules superposées
        for second in cells:
            if first["id"] >= second["id"]:
                continue
            overlap_w = min(first["x"] + first["w"], second["x"] + second["w"]) - max(
                first["x"], second["x"]
            )
            overlap_h = min(first["y"] + first["h"], second["y"] + second["h"]) - max(
                first["y"], second["y"]
            )
            assert overlap_w <= 0 or overlap_h <= 0, (first, second)


def test_treemap_is_deterministic_and_skips_zero_values() -> None:
    dashboard_one = build_dashboard(_graph(), Config(), _page_for)
    dashboard_two = build_dashboard(_graph(), Config(), _page_for)
    assert dashboard_one == dashboard_two
    treemap = dashboard_one["treemap"]
    assert treemap["metric"] == "complexity"  # défaut de [explorer].default_metric
    # complexité nulle partout dans ce graphe → repli sur les lignes de code
    assert treemap["fallback"] == "loc"
    ids = {c["id"] for c in treemap["cells"]}
    assert "main/app.gamma" not in ids  # valeur nulle : jamais de cellule invisible
    assert treemap["omitted"] == 1


def test_treemap_svg_is_clickable_and_self_contained() -> None:
    dashboard = build_dashboard(_graph(), Config(), _page_for)
    svg = render_treemap_svg(dashboard["treemap"])
    assert svg.startswith("<svg")
    assert 'href="modules/app.alpha.html"' in svg
    assert "<title>" in svg  # libellé + valeur au survol
    assert "http" not in svg  # aucune ressource externe
