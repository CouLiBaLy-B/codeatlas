"""API bibliothèque publique de CodeAtlas (constitution II).

La CLI n'est qu'une façade au-dessus de ces quatre fonctions :
`analyze`, `build_site`, `render_diagram`, `run_checks`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from codeatlas.baseline.capture import Baseline
    from codeatlas.baseline.compare import ArchDelta

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


def _reroot_fragment(fragment: object, prefix: str) -> None:
    """Re-préfixe les chemins d'un fragment par le répertoire du sous-projet."""
    from dataclasses import replace as _replace

    from codeatlas.analyzers.base import IRFragment
    from codeatlas.ir.model import Location, SkippedFile

    assert isinstance(fragment, IRFragment)
    if prefix in ("", "."):
        return

    def _fix(location: Location | None) -> Location | None:
        if location is None:
            return None
        return Location(file=f"{prefix}/{location.file}", line=location.line)

    fragment.nodes = [_replace(n, location=_fix(n.location)) for n in fragment.nodes]  # type: ignore[arg-type]
    fragment.edges = [_replace(e, location=_fix(e.location)) for e in fragment.edges]
    fragment.skipped = [
        SkippedFile(path=f"{prefix}/{s.path}", reason=s.reason) for s in fragment.skipped
    ]


def _analyze_single(root: Path, cfg: Config, graph: CodeGraph) -> bool:
    """Dépôt simple : tous les analyseurs disponibles sur la racine."""
    options = AnalyzerOptions(include_private=cfg.analysis.include_private)
    analyzed_any = False
    main_taken = False
    for language, analyzer in available_analyzers().items():
        if cfg.analysis.languages and language not in cfg.analysis.languages:
            continue
        files, unreadable = discover_files(root, cfg.analysis.exclude, analyzer.extensions)
        if not files and not unreadable:
            continue
        sub_id = "main" if not main_taken else f"main-{language}"
        main_taken = True
        subproject = SubProject(id=sub_id, language=language, root=".")
        graph.add_subproject(subproject)
        fragment = analyzer.analyze(files, subproject, options)
        for node in fragment.nodes:
            graph.add_node(node)
        for edge in fragment.edges:
            graph.add_edge(edge)
        for skipped in (*unreadable, *fragment.skipped):
            graph.add_skipped(skipped)
        analyzed_any = analyzed_any or bool(fragment.nodes)
    return analyzed_any


def _analyze_monorepo(root: Path, cfg: Config, graph: CodeGraph, subs: list[SubProject]) -> bool:
    """Monorepo : chaque sous-projet analysé par l'analyseur de son langage."""
    from codeatlas.ir.model import Edge, EdgeKind

    options = AnalyzerOptions(include_private=cfg.analysis.include_private)
    analyzers = available_analyzers()
    analyzed_any = False
    for sub in subs:
        graph.add_subproject(sub)
    for sub in subs:
        if cfg.analysis.languages and sub.language not in cfg.analysis.languages:
            continue  # filtre [analysis].languages (FR-017, T087)
        analyzer = analyzers.get(sub.language)
        if analyzer is None:
            continue  # langage non supporté : listé, jamais bloquant (US6 scénario 3)
        sub_dir = root if sub.root == "." else root / sub.root
        files, unreadable = discover_files(sub_dir, cfg.analysis.exclude, analyzer.extensions)
        nested = [
            other.root
            for other in subs
            if other.root != sub.root
            and (sub.root == "." or other.root.startswith(f"{sub.root}/"))
        ]
        kept = []
        for source in files:
            full = source.path if sub.root == "." else f"{sub.root}/{source.path}"
            if any(full == n or full.startswith(f"{n}/") for n in nested):
                continue
            kept.append(source)
        fragment = analyzer.analyze(kept, sub, options)
        _reroot_fragment(fragment, sub.root)
        for node in fragment.nodes:
            graph.add_node(node)
        for edge in fragment.edges:
            graph.add_edge(edge)
        prefix = "" if sub.root == "." else f"{sub.root}/"
        for skipped in fragment.skipped:
            graph.add_skipped(skipped)
        for skipped in unreadable:
            graph.add_skipped(
                type(skipped)(path=f"{prefix}{skipped.path}", reason=skipped.reason)
            )
        analyzed_any = analyzed_any or bool(fragment.nodes)
    for sub in subs:
        for dep_id in sub.declared_deps:
            graph.add_edge(Edge(source=sub.id, target=dep_id, kind=EdgeKind.SERVICE_DEP))
    # imports croisés détectés dans les sources (T085) : ext-import:<nom de package>
    name_to_id = {sub.name: sub.id for sub in subs if sub.name}
    for module in graph.iter_nodes():
        if module.kind.value != "module":
            continue
        for modifier in sorted(module.modifiers):
            if not modifier.startswith("ext-import:"):
                continue
            target_id = name_to_id.get(modifier.removeprefix("ext-import:"))
            if target_id is not None and target_id != module.subproject:
                graph.add_edge(
                    Edge(source=module.subproject, target=target_id, kind=EdgeKind.SERVICE_DEP)
                )
    return analyzed_any


def analyze(path: Path, config: Config | None = None) -> CodeGraph:
    """Analyse statique d'un dépôt (simple ou monorepo) → graphe de code (IR).

    Tolérante : les fichiers non parsables deviennent des entrées `skipped`.
    Lève CodeAtlasError seulement si RIEN n'est analysable (constitution IV).
    """
    from codeatlas.monorepo.detect import detect_subprojects

    root = path.resolve()
    if not root.is_dir():
        raise CodeAtlasError(f"répertoire introuvable : {path}")
    cfg = config if config is not None else load_config(root)

    graph = CodeGraph(root=root.name)
    subs = (
        detect_subprojects(root, cfg.analysis.exclude, roots=tuple(cfg.monorepo.roots))
        if cfg.monorepo.detect
        else []
    )
    if len(subs) > 1:
        analyzed_any = _analyze_monorepo(root, cfg, graph, subs)
    else:
        analyzed_any = _analyze_single(root, cfg, graph)

    if not analyzed_any:
        raise CodeAtlasError(
            f"aucun fichier analysable trouvé dans {path} "
            "(langages supportés installés : "
            f"{', '.join(available_analyzers())})"
        )
    return graph


def build_site(
    graph: CodeGraph,
    out: Path,
    config: Config | None = None,
    source_root: Path | None = None,
) -> AnalysisReport:
    """Génère les artefacts (.md/.mmd) et le site dans `out` → rapport d'exécution."""
    from codeatlas.site.builder import build as _build

    cfg = config if config is not None else Config()
    return _build(graph, out, cfg, source_root=source_root)


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
        from codeatlas.renderers.mermaid.class_diagram import render_class_neighborhood

        node_id = _resolve_focus(
            graph,
            spec.focus,
            (NodeKind.MODULE, NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM),
        )
        node = graph.nodes[node_id]
        if node.kind is NodeKind.MODULE:
            return render_class_diagram(graph, node_id, cfg.analysis.include_private)
        # classe focale : voisinage à rayon N (FR-010)
        return render_class_neighborhood(
            graph, node_id, spec.depth or cfg.graphs.focus_depth, cfg.analysis.include_private
        )
    raise FocusError(f"type de diagramme inconnu : {spec.type!r}")


def run_checks(
    graph: CodeGraph, thresholds: CheckCfg, config: Config | None = None
) -> list[CheckResult]:
    """Évalue les seuils qualité du mode CI (`codeatlas check`)."""
    from codeatlas.insights.checks import run_checks as _run

    return _run(graph, thresholds, config if config is not None else Config())


def capture_baseline(graph: CodeGraph, config: Config | None = None) -> Baseline:
    """Capture le résumé architectural courant (feature 002)."""
    from codeatlas.baseline.capture import capture

    return capture(graph, config if config is not None else Config())


def diff_baseline(
    graph: CodeGraph, baseline: Baseline, config: Config | None = None
) -> ArchDelta:
    """Compare l'état courant à une baseline → ArchDelta (feature 002)."""
    from codeatlas.baseline.capture import capture
    from codeatlas.baseline.compare import compare

    current = capture(graph, config if config is not None else Config())
    return compare(baseline, current)
