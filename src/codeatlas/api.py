"""API bibliothèque publique de CodeAtlas (constitution II).

La CLI n'est qu'une façade au-dessus de ces quatre fonctions :
`analyze`, `build_site`, `render_diagram`, `run_checks`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from codeatlas.analyzers.base import AnalyzerOptions, available_analyzers, discover_files
from codeatlas.config import CheckCfg, Config, load_config
from codeatlas.ir.model import CodeGraph, NodeKind, SubProject
from codeatlas.report.model import AnalysisReport, CheckResult


class CodeAtlasError(Exception):
    """Erreur fatale d'exécution (exit 1 côté CLI)."""


class FocusError(CodeAtlasError):
    """Symbole focal introuvable ou ambigu (erreur d'usage, exit 2 côté CLI)."""


class FeatureUnavailableError(CodeAtlasError):
    """Capacité prévue par le contrat mais pas encore livrée (story ultérieure)."""


@dataclass(frozen=True, slots=True)
class DiagramSpec:
    """Spécification d'un diagramme focalisé (contrat cli.md)."""

    type: str  # "class" | "deps" | "calls"
    focus: str | None = None
    depth: int | None = None


def analyze(path: Path, config: Config | None = None) -> CodeGraph:
    """Analyse statique d'un dépôt → graphe de code (IR).

    Tolérante : les fichiers non parsables deviennent des entrées `skipped`.
    Lève CodeAtlasError seulement si RIEN n'est analysable (constitution IV).
    """
    root = path.resolve()
    if not root.is_dir():
        raise CodeAtlasError(f"répertoire introuvable : {path}")
    cfg = config if config is not None else load_config(root)

    graph = CodeGraph(root=root.name)
    options = AnalyzerOptions(include_private=cfg.analysis.include_private)

    analyzed_any = False
    for language, analyzer in available_analyzers().items():
        if cfg.analysis.languages and language not in cfg.analysis.languages:
            continue
        subproject = SubProject(id="main", language=language, root=".")
        files, unreadable = discover_files(root, cfg.analysis.exclude, analyzer.extensions)
        if not files and not unreadable:
            continue
        graph.add_subproject(subproject)
        fragment = analyzer.analyze(files, subproject, options)
        for node in fragment.nodes:
            graph.add_node(node)
        for edge in fragment.edges:
            graph.add_edge(edge)
        for skipped in (*unreadable, *fragment.skipped):
            graph.add_skipped(skipped)
        if len(fragment.nodes) > 0:
            analyzed_any = True

    if not analyzed_any:
        raise CodeAtlasError(
            f"aucun fichier analysable trouvé dans {path} "
            "(langages supportés installés : "
            f"{', '.join(available_analyzers())})"
        )
    return graph


def build_site(graph: CodeGraph, out: Path, config: Config | None = None) -> AnalysisReport:
    """Génère les artefacts (.md/.mmd) et le site dans `out` → rapport d'exécution."""
    from codeatlas.site.builder import build as _build

    cfg = config if config is not None else Config()
    return _build(graph, out, cfg)


def _resolve_focus(graph: CodeGraph, focus: str, kinds: tuple[NodeKind, ...]) -> str:
    """Résout un nom qualifié ou un nom court non ambigu vers un id de nœud."""
    candidates = []
    for node in graph.iter_nodes():
        if node.kind not in kinds:
            continue
        qualname = node.id.split("/", 1)[-1]
        if node.id == focus or qualname == focus or qualname.endswith(f".{focus}"):
            candidates.append(node.id)
    if not candidates:
        raise FocusError(f"symbole focal introuvable : {focus!r}")
    if len(candidates) > 1:
        listing = ", ".join(candidates)
        raise FocusError(f"symbole focal ambigu : {focus!r} — candidats : {listing}")
    return candidates[0]


def render_diagram(graph: CodeGraph, spec: DiagramSpec, config: Config | None = None) -> str:
    """Diagramme focalisé (`codeatlas diagram`) : class, deps ou calls."""
    from codeatlas.renderers.mermaid.call_flow import render_call_flow
    from codeatlas.renderers.mermaid.class_diagram import render_class_diagram
    from codeatlas.renderers.mermaid.package_deps import render_package_deps

    cfg = config if config is not None else Config()
    if spec.type == "deps":
        return render_package_deps(graph)
    if spec.focus is None:
        raise FocusError(f"--focus est requis pour un diagramme de type {spec.type!r}")

    if spec.type == "calls":
        node_id = _resolve_focus(graph, spec.focus, (NodeKind.FUNCTION, NodeKind.METHOD))
        return render_call_flow(graph, node_id, spec.depth or cfg.graphs.call_depth)
    if spec.type == "class":
        node_id = _resolve_focus(
            graph,
            spec.focus,
            (NodeKind.MODULE, NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM),
        )
        node = graph.nodes[node_id]
        module_id = node_id if node.kind is NodeKind.MODULE else node_id.rsplit(".", 1)[0]
        return render_class_diagram(graph, module_id, cfg.analysis.include_private)
    raise FocusError(f"type de diagramme inconnu : {spec.type!r}")


def run_checks(
    graph: CodeGraph, thresholds: CheckCfg, config: Config | None = None
) -> list[CheckResult]:
    """Évalue les seuils qualité du mode CI (`codeatlas check`)."""
    from codeatlas.insights.checks import run_checks as _run

    return _run(graph, thresholds, config if config is not None else Config())
