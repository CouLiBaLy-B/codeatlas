"""API bibliothèque publique de CodeAtlas (constitution II).

La CLI n'est qu'une façade au-dessus de ces quatre fonctions :
`analyze`, `build_site`, `render_diagram`, `run_checks`.
"""

from __future__ import annotations

from pathlib import Path

from codeatlas.analyzers.base import AnalyzerOptions, available_analyzers, discover_files
from codeatlas.config import Config, load_config
from codeatlas.ir.model import CodeGraph, SubProject
from codeatlas.report.model import AnalysisReport, CheckResult


class CodeAtlasError(Exception):
    """Erreur fatale d'exécution (exit 1 côté CLI)."""


class FeatureUnavailableError(CodeAtlasError):
    """Capacité prévue par le contrat mais pas encore livrée (story ultérieure)."""


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


def render_diagram(graph: CodeGraph, spec: object) -> str:
    """Diagramme focalisé (US2 — `codeatlas diagram`)."""
    raise FeatureUnavailableError(
        "render_diagram sera livré avec la user story 2 (graphes d'appels)"
    )


def run_checks(graph: CodeGraph, thresholds: object) -> list[CheckResult]:
    """Seuils du mode CI (US4 — `codeatlas check`)."""
    raise FeatureUnavailableError("run_checks sera livré avec la user story 4 (mode CI)")
