"""T010 — Les répertoires générés ne polluent pas l'analyse (US3, SC-005)."""

from __future__ import annotations

from pathlib import Path

from codeatlas import api
from codeatlas.analyzers.base import GENERATED_MARKER, discover_files
from codeatlas.ir.model import NodeKind

PY = frozenset({".py"})


def test_discover_files_skips_marked_directories(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    generated = tmp_path / "codeatlas-docs"
    generated.mkdir()
    (generated / GENERATED_MARKER).write_text("", encoding="utf-8")
    (generated / "leak.py").write_text("y = 2\n", encoding="utf-8")

    sources, _ = discover_files(tmp_path, (), PY)
    paths = {s.path for s in sources}
    assert "pkg/mod.py" in paths
    assert not any(p.startswith("codeatlas-docs/") for p in paths)  # marqueur → ignoré


def test_full_analysis_excludes_generated_site(tmp_path: Path) -> None:
    """Un site généré imbriqué ne crée ni module ni sous-projet parasite."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "core.py").write_text("def run() -> None:\n    pass\n", encoding="utf-8")
    # site généré : marqueur + un script JS vendorisé qui créerait un faux sous-projet JS
    site = tmp_path / "app-docs"
    (site / "assets").mkdir(parents=True)
    (site / GENERATED_MARKER).write_text("", encoding="utf-8")
    (site / "assets" / "vendor.js").write_text("console.log(1);\n", encoding="utf-8")

    graph = api.analyze(tmp_path)
    files = {n.location.file for n in graph.iter_nodes(NodeKind.MODULE)}
    assert not any("app-docs" in f for f in files)
    assert [s.language for s in graph.subprojects] == ["python"]  # aucun sous-projet JS


def test_marker_can_be_overridden_by_explicit_reinclusion(tmp_path: Path) -> None:
    """L'utilisateur garde la main : le marqueur n'est pas une exclusion figée."""
    generated = tmp_path / "gen"
    generated.mkdir()
    (generated / GENERATED_MARKER).write_text("", encoding="utf-8")
    (generated / "keep.py").write_text("z = 3\n", encoding="utf-8")
    # include_generated=True désactive le filtrage par marqueur
    sources, _ = discover_files(tmp_path, (), PY, include_generated=True)
    assert any(s.path == "gen/keep.py" for s in sources)


def test_builder_writes_generation_marker(tmp_path: Path) -> None:
    from codeatlas.config import Config, SiteCfg
    from codeatlas.ir.model import CodeGraph, Location, Node, SubProject

    graph = CodeGraph(root="demo")
    graph.add_subproject(SubProject(id="main", language="python", root="."))
    graph.add_node(
        Node(
            id="main/m",
            kind=NodeKind.MODULE,
            name="m",
            subproject="main",
            location=Location(file="m.py", line=1),
        )
    )
    out = tmp_path / "out"
    api.build_site(graph, out, Config(site=SiteCfg(enabled=False)))
    assert (out / GENERATED_MARKER).is_file()  # site marqué comme généré
