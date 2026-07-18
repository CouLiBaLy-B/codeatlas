"""Builder du site : artefacts markdown/mermaid + site MkDocs Material hors-ligne.

Garanties (contracts/cli.md) :
- écritures UTF-8 avec fins de ligne `\\n` (déterminisme cross-OS) ;
- remplacement atomique du répertoire de sortie ;
- aucun horodatage dans les artefacts (SOURCE_DATE_EPOCH figé pour mkdocs) ;
- mermaid.min.js vendorisé, aucun CDN.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from codeatlas.config import Config
from codeatlas.insights.patterns import detect_patterns
from codeatlas.ir.model import CodeGraph, NodeKind
from codeatlas.renderers.mermaid.class_diagram import render_class_diagram
from codeatlas.renderers.mermaid.package_deps import render_package_deps
from codeatlas.report.model import AnalysisReport, Warning_
from codeatlas.site.i18n import labels
from codeatlas.site.pages import (
    module_display_name,
    page_slug,
    render_architecture_page,
    render_changelog_page,
    render_entrypoints_page,
    render_health_page,
    render_index_page,
    render_module_page,
    render_monorepo_page,
    render_tour_page,
)

_ASSETS = Path(__file__).parent / "assets"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _module_qualname(module_id: str) -> str:
    return module_id.split("/", 1)[1] if "/" in module_id else module_id


def _explorer_scripts() -> list[str]:
    """Scripts des vues interactives, dans l'ordre de chargement (données d'abord)."""
    return [
        "assets/data/atlas-graph.js",
        "assets/data/atlas-search.js",
        "assets/data/atlas-dashboard.js",
        "assets/cytoscape.min.js",
        *(f"assets/{p.name}" for p in sorted(_ASSETS.glob("atlas-*.js"))),
    ]


def _mkdocs_yml(graph: CodeGraph, config: Config, extra_pages: list[tuple[str, str]]) -> str:
    translations = labels(config.project.language)
    title = config.project.title or graph.root
    lines = [
        f"site_name: {title}",
        "docs_dir: docs",
        "site_dir: site",
        "use_directory_urls: false",
        "theme:",
        "  name: material",
        f"  language: {config.project.language}",
        "  font: false",
        "markdown_extensions:",
        "  - admonition",
        "  - pymdownx.details",
        "  - pymdownx.highlight:",
        "      use_pygments: false",  # budget SC-005 : pas de lexing des extraits au build
        "  - pymdownx.superfences:",
        "      custom_fences:",
        "        - name: mermaid",
        "          class: mermaid",
        "          format: !!python/name:pymdownx.superfences.fence_div_format",
        "extra_javascript:",
        "  - assets/mermaid.min.js",
        "  - assets/mermaid-init.js",
        *(f"  - {script}" for script in (_explorer_scripts() if config.explorer.enabled else [])),
        "nav:",
        f"  - {translations['overview']}: index.md",
    ]
    for nav_label, filename in extra_pages:
        lines.append(f"  - {nav_label}: {filename}")
    lines.append(f"  - {translations['modules']}:")
    for module in graph.iter_nodes(NodeKind.MODULE):
        display = module_display_name(graph, module.id)
        lines.append(f"      - {display}: modules/{page_slug(graph, module.id)}.md")
    for extra in config.site.extra_nav:
        lines.append(f"  - {extra}")
    return "\n".join(lines) + "\n"


def _build_html_site(staging: Path, report: AnalysisReport) -> None:
    """Construit le site HTML via mkdocs, de façon reproductible et hors-ligne."""
    try:
        from mkdocs.commands.build import build as mkdocs_build
        from mkdocs.config import load_config as mkdocs_load_config
    except ImportError:
        report.warnings.append(
            Warning_(
                code="site-unavailable",
                where="mkdocs",
                detail="extra [site] non installé — pip install 'codeatlas[site]'",
            )
        )
        return

    previous = os.environ.get("SOURCE_DATE_EPOCH")
    os.environ["SOURCE_DATE_EPOCH"] = "0"
    try:
        mkdocs_config = mkdocs_load_config(config_file=str(staging / "mkdocs.yml"))
        mkdocs_config["site_dir"] = str(staging / "site")
        mkdocs_build(mkdocs_config)
    finally:
        if previous is None:
            del os.environ["SOURCE_DATE_EPOCH"]
        else:  # pragma: no cover — restauration d'un env préexistant
            os.environ["SOURCE_DATE_EPOCH"] = previous


def build(
    graph: CodeGraph, out: Path, config: Config, source_root: Path | None = None
) -> AnalysisReport:
    """Génère docs/, diagrams/, mkdocs.yml et (si activé) site/ dans `out`."""
    report = AnalysisReport(root=graph.root)
    report.subprojects = [
        {
            "id": sub.id,
            "language": sub.language,
            "files_analyzed": sum(
                1 for n in graph.iter_nodes(NodeKind.MODULE) if n.subproject == sub.id
            ),
        }
        for sub in graph.subprojects
    ]
    report.files_analyzed = sum(1 for _ in graph.iter_nodes(NodeKind.MODULE))
    report.files_skipped = len(graph.skipped)
    report.nodes = len(graph.nodes)
    report.edges_certain = sum(1 for e in graph.edges if e.certainty.value == "certain")
    report.edges_inferred = sum(1 for e in graph.edges if e.certainty.value == "inferred")
    report.skipped = [{"path": s.path, "reason": s.reason} for s in graph.skipped]

    staging = out.parent / f".{out.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        docs = staging / "docs"
        translations = labels(config.project.language)
        extra_pages: list[tuple[str, str]] = []

        # Données des vues interactives et relations : calculées UNE fois par build.
        explorer_data = None
        relations_index = None
        if config.explorer.enabled:
            from codeatlas.api import build_explorer_data
            from codeatlas.site.pages import build_relations_index

            explorer_data = build_explorer_data(graph, config)
            relations_index = build_relations_index(graph)
        _write(docs / "index.md", render_index_page(graph, config))
        _write(staging / "diagrams" / "package_deps.mmd", render_package_deps(graph))

        monorepo_page = render_monorepo_page(graph, config)
        if monorepo_page is not None:
            _write(docs / "monorepo.md", monorepo_page)
            extra_pages.append((translations["monorepo"], "monorepo.md"))

        entrypoints_page = render_entrypoints_page(graph, config)
        if entrypoints_page is not None:
            _write(docs / "entrypoints.md", entrypoints_page)
            extra_pages.append((translations["entry_points"], "entrypoints.md"))

        tour_page = render_tour_page(graph, config)
        if tour_page is not None:
            _write(docs / "tour.md", tour_page)
            extra_pages.append((translations["tour"], "tour.md"))

        architecture_page = render_architecture_page(
            graph, config, explorer=config.explorer.enabled
        )
        if architecture_page is not None:
            _write(docs / "architecture.md", architecture_page)
            extra_pages.append((translations["architecture"], "architecture.md"))

        _write(
            docs / "health.md",
            render_health_page(
                graph,
                config,
                dashboard=explorer_data.dashboard if explorer_data is not None else None,
            ),
        )
        extra_pages.append((translations["health"], "health.md"))

        if source_root is not None:
            changelog_page = render_changelog_page(source_root, config)
            if changelog_page is not None:
                _write(docs / "changelog.md", changelog_page)
                extra_pages.append((translations["changelog"], "changelog.md"))

        patterns = {d.class_id: d for d in detect_patterns(graph)}
        for module in graph.iter_nodes(NodeKind.MODULE):
            slug = page_slug(graph, module.id)
            _write(
                docs / "modules" / f"{slug}.md",
                render_module_page(
                    graph,
                    module.id,
                    config,
                    patterns,
                    explorer=config.explorer.enabled,
                    source_root=source_root if config.explorer.include_source else None,
                    relations=relations_index,
                ),
            )
            diagram = render_class_diagram(graph, module.id, config.analysis.include_private)
            if "class " in diagram:  # n'émet un artefact que si le module a des classes
                _write(staging / "diagrams" / f"{slug}.mmd", diagram)

        # Pages manuelles [site].extra_nav : préservées depuis la sortie précédente,
        # échafaudées au premier build — JAMAIS écrasées (contrat cli.md).
        for extra in config.site.extra_nav:
            target = docs / extra
            previous = out / "docs" / extra
            target.parent.mkdir(parents=True, exist_ok=True)
            if previous.is_file():
                shutil.copyfile(previous, target)
            elif not target.exists():
                stub = (
                    f"# {extra}\n\n"
                    "<!-- Page manuelle : ce fichier ne sera jamais écrasé par CodeAtlas. -->\n"
                )
                _write(target, stub)

        if config.site.svg_export:
            report.warnings.append(
                Warning_(
                    code="svg-unavailable",
                    where="site",
                    detail=(
                        "export SVG non supporté dans cette version (nécessite un moteur "
                        "JS) — option ignorée, les diagrammes restent en Mermaid (.mmd)"
                    ),
                )
            )

        assets_dir = docs / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        explorer_assets = {"cytoscape.min.js", *(p.name for p in _ASSETS.glob("atlas-*.js"))}
        for asset in sorted(_ASSETS.iterdir()):
            if not config.explorer.enabled and asset.name in explorer_assets:
                continue  # --no-explorer : site strictement équivalent à la feature 001
            shutil.copyfile(asset, assets_dir / asset.name)

        if explorer_data is not None:
            from codeatlas.explorer.emit import write_data

            write_data(explorer_data, docs)

        _write(staging / "mkdocs.yml", _mkdocs_yml(graph, config, extra_pages))

        if config.site.enabled:
            _build_html_site(staging, report)

        if out.exists():
            shutil.rmtree(out)
        staging.rename(out)
    finally:
        if staging.exists():  # pragma: no cover — nettoyage sur erreur
            shutil.rmtree(staging)
    return report
