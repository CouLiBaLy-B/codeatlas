"""T027 — Extraits de source exacts sur les fiches (US5, FR-016/017)."""

from __future__ import annotations

from pathlib import Path

from codeatlas.config import Config, ExplorerCfg
from codeatlas.explorer.source import extract_excerpt
from codeatlas.ir.model import (
    Certainty,
    CodeGraph,
    Edge,
    EdgeKind,
    Location,
    Node,
    NodeKind,
    SubProject,
)
from codeatlas.site.pages import render_module_page


def _node(node_id: str, kind: NodeKind, file: str, line: int, loc: int = 0) -> Node:
    return Node(
        id=node_id,
        kind=kind,
        name=node_id.rsplit(".", 1)[-1],
        subproject="main",
        location=Location(file=file, line=line),
        loc=loc,
    )


def test_excerpt_matches_exact_definition_lines(tmp_path: Path) -> None:
    source = tmp_path / "mod.py"
    source.write_text(
        "import os\n\n\ndef target():\n    a = 1\n    return a\n\n\ndef after():\n    pass\n",
        encoding="utf-8",
    )
    node = _node("main/mod.target", NodeKind.FUNCTION, "mod.py", line=4, loc=3)
    excerpt = extract_excerpt(tmp_path, node)
    assert excerpt is not None
    assert (excerpt.start_line, excerpt.end_line) == (4, 6)
    assert excerpt.code == "def target():\n    a = 1\n    return a"


def test_unreadable_file_yields_none(tmp_path: Path) -> None:
    node = _node("main/gone.fn", NodeKind.FUNCTION, "gone.py", line=1, loc=2)
    assert extract_excerpt(tmp_path, node) is None


def test_exotic_encoding_is_tolerated(tmp_path: Path) -> None:
    (tmp_path / "legacy.py").write_bytes(b"def caf\xe9():\n    pass\n")  # latin-1
    node = _node("main/legacy.cafe", NodeKind.FUNCTION, "legacy.py", line=1, loc=2)
    excerpt = extract_excerpt(tmp_path, node)
    assert excerpt is not None and "def caf" in excerpt.code


def _page_graph() -> CodeGraph:
    graph = CodeGraph(root="demo")
    graph.add_subproject(SubProject(id="main", language="python", root="."))
    graph.add_node(_node("main/mod", NodeKind.MODULE, "mod.py", line=1, loc=6))
    graph.add_node(_node("main/mod.target", NodeKind.FUNCTION, "mod.py", line=4, loc=3))
    graph.add_node(_node("main/other", NodeKind.MODULE, "other.py", line=1, loc=3))
    graph.add_node(_node("main/other.caller", NodeKind.FUNCTION, "other.py", line=1, loc=2))
    graph.add_edge(
        Edge(
            source="main/other.caller",
            target="main/mod.target",
            kind=EdgeKind.CALLS,
            certainty=Certainty.INFERRED,
        )
    )
    return graph


def _write_sources(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(
        "import os\n\n\ndef target():\n    a = 1\n    return a\n", encoding="utf-8"
    )
    (tmp_path / "other.py").write_text(
        "def caller():\n    target()\n", encoding="utf-8"
    )


def test_module_page_embeds_excerpt_and_callers(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    page = render_module_page(
        _page_graph(), "main/mod", Config(), explorer=True, source_root=tmp_path
    )
    assert "def target():" in page  # extrait exact
    assert "mod.py:4" in page
    assert "other.caller" in page  # appelant cliquable
    assert "(modules/other.md#caller)" in page
    assert "incertain" in page or "uncertain" in page  # lien incertain distingué


def test_include_source_false_removes_all_excerpts(tmp_path: Path) -> None:
    _write_sources(tmp_path)
    config = Config(explorer=ExplorerCfg(include_source=False))
    page = render_module_page(
        _page_graph(), "main/mod", config, explorer=True, source_root=tmp_path
    )
    assert "def target():" not in page
    assert "other.caller" in page  # les relations restent (indépendantes de la source)


def test_unreadable_source_is_flagged_explicitly(tmp_path: Path) -> None:
    (tmp_path / "other.py").write_text("def caller():\n    target()\n", encoding="utf-8")
    page = render_module_page(  # mod.py absent : la fiche l'indique, pas de zone vide
        _page_graph(), "main/mod", Config(), explorer=True, source_root=tmp_path
    )
    assert "def target():" not in page
    assert "non disponible" in page or "unavailable" in page
