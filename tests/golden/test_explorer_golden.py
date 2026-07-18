"""T011/T015/T026 — Goldens des données de vues interactives (corpus python-demo)."""

from __future__ import annotations

from pathlib import Path

from codeatlas import api
from codeatlas.explorer.emit import write_data

from .corpus import corpus_graph


def _emitted(tmp_path: Path, name: str) -> str:
    data = api.build_explorer_data(corpus_graph())
    write_data(data, tmp_path)
    return (tmp_path / "assets" / "data" / name).read_text(encoding="utf-8")


def test_atlas_graph_matches_golden(assert_golden, tmp_path: Path) -> None:
    assert_golden("atlas-graph.js", _emitted(tmp_path, "atlas-graph.js"))


def test_atlas_search_matches_golden(assert_golden, tmp_path: Path) -> None:
    assert_golden("atlas-search.js", _emitted(tmp_path, "atlas-search.js"))


def test_atlas_dashboard_matches_golden(assert_golden, tmp_path: Path) -> None:
    assert_golden("atlas-dashboard.js", _emitted(tmp_path, "atlas-dashboard.js"))


def test_treemap_svg_matches_golden(assert_golden) -> None:
    from codeatlas.config import Config
    from codeatlas.explorer.dashboard import build_dashboard, render_treemap_svg

    def page_for(module_id: str) -> str:
        return f"modules/{module_id.split('/', 1)[-1]}.html"

    dashboard = build_dashboard(corpus_graph(), Config(), page_for)
    subproject_of = {row["id"]: row["subproject"] for row in dashboard["rows"]}
    assert_golden("treemap.svg", render_treemap_svg(dashboard["treemap"], subproject_of))
