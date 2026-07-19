"""T007 — Validation grandeur nature : CodeAtlas lui-même est en layout src/ (SC-001/002)."""

from __future__ import annotations

from pathlib import Path

from codeatlas import api
from codeatlas.ir.model import EdgeKind, NodeKind

REPO = Path(__file__).parents[2]


def test_codeatlas_self_analysis_resolves_imports_from_repo_root() -> None:
    """Analysé depuis la racine du dépôt (layout src/), le graphe est connecté."""
    graph = api.analyze(REPO / "src")
    module_ids = {n.id.split("/", 1)[-1] for n in graph.iter_nodes(NodeKind.MODULE)}
    assert "codeatlas.api" in module_ids  # nom importable, pas `src.codeatlas.api`
    imports = graph.edges_of_kind(EdgeKind.IMPORTS)
    assert len(imports) > 100, f"imports résolus : {len(imports)} (attendu > 100, SC-001)"


def test_coupling_is_non_zero(tmp_path: Path) -> None:
    """SC-002 : le couplage (fan-in/fan-out) n'est plus nul sur un projet src/."""
    from codeatlas.config import Config
    from codeatlas.insights.metrics import compute_metrics

    graph = api.analyze(REPO / "src")
    health = compute_metrics(graph, Config())
    assert any(row.fan_in > 0 or row.fan_out > 0 for row in health.modules)
