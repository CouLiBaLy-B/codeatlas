"""T011 — Intégration build avec vues interactives (US1) : assets, déterminisme, opt-out."""

from __future__ import annotations

import filecmp
from pathlib import Path

from codeatlas.cli import main


def _build(runner, corpus: Path, out: Path, *extra: str):
    result = runner.invoke(
        main, ["build", str(corpus), "--out", str(out), "--no-site", "--quiet", *extra]
    )
    assert result.exit_code == 0, result.output
    return out


def test_build_emits_explorer_assets_and_data(runner, corpus: Path, tmp_path: Path) -> None:
    out = _build(runner, corpus, tmp_path / "docs")
    assets = out / "docs" / "assets"
    assert (assets / "cytoscape.min.js").is_file()
    assert (assets / "atlas-explorer.js").is_file()
    data = assets / "data"
    for name in ("atlas-graph.js", "atlas-search.js", "atlas-dashboard.js"):
        assert (data / name).is_file(), name
    mkdocs = (out / "mkdocs.yml").read_text(encoding="utf-8")
    assert "assets/data/atlas-graph.js" in mkdocs
    assert "assets/cytoscape.min.js" in mkdocs


def test_architecture_page_hosts_explorer_with_static_fallback(
    runner, corpus: Path, tmp_path: Path
) -> None:
    out = _build(runner, corpus, tmp_path / "docs")
    page = (out / "docs" / "architecture.md").read_text(encoding="utf-8")
    assert '<div id="atlas-explorer"' in page  # conteneur de la vue interactive
    assert "```mermaid" in page  # repli statique toujours présent (FR-005)


def test_two_builds_are_byte_for_byte_identical(runner, corpus: Path, tmp_path: Path) -> None:
    first = _build(runner, corpus, tmp_path / "one")
    second = _build(runner, corpus, tmp_path / "two")
    comparison = filecmp.dircmp(first, second)
    differences: list[str] = []

    def _collect(cmp) -> None:
        differences.extend(cmp.diff_files + cmp.left_only + cmp.right_only + cmp.funny_files)
        for sub in cmp.subdirs.values():
            _collect(sub)

    _collect(comparison)
    assert differences == []


def test_no_explorer_produces_feature_001_site(runner, corpus: Path, tmp_path: Path) -> None:
    out = _build(runner, corpus, tmp_path / "docs", "--no-explorer")
    assets = out / "docs" / "assets"
    assert not (assets / "cytoscape.min.js").exists()
    assert not list(assets.glob("atlas-*.js"))
    assert not (assets / "data").exists()
    mkdocs = (out / "mkdocs.yml").read_text(encoding="utf-8")
    assert "atlas" not in mkdocs and "cytoscape" not in mkdocs
    architecture = out / "docs" / "architecture.md"
    if architecture.exists():
        assert "atlas-explorer" not in architecture.read_text(encoding="utf-8")
