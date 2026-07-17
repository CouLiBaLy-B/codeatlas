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
from codeatlas.ir.model import CodeGraph, NodeKind
from codeatlas.renderers.mermaid.class_diagram import render_class_diagram
from codeatlas.renderers.mermaid.package_deps import render_package_deps
from codeatlas.report.model import AnalysisReport, Warning_
from codeatlas.site.i18n import labels
from codeatlas.insights.patterns import detect_patterns
from codeatlas.site.pages import (
    module_display_name,
    page_slug,
    render_architecture_page,
    render_entrypoints_page,
    render_health_page,
    render_index_page,
    render_module_page,
    render_monorepo_page,
)

_ASSETS = Path(__file__).parent / "assets"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _module_qualname(module_id: str) -> str:
    return module_id.split("/", 1)[1] if "/" in module_id else module_id


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
        "  - pymdownx.superfences:",
        "      custom_fences:",
        "        - name: mermaid",
        "          class: mermaid",
        "          format: !!python/name:pymdownx.superfences.fence_div_format",
        "extra_javascript:",
        "  - assets/mermaid.min.js",
        "  - assets/mermaid-init.js",
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


def build(graph: CodeGraph, out: Path, config: Config) -> AnalysisReport:
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

        architecture_page = render_architecture_page(graph, config)
        if architecture_page is not None:
            _write(docs / "architecture.md", architecture_page)
            extra_pages.append((translations["architecture"], "architecture.md"))

        _write(docs / "health.md", render_health_page(graph, config))
        extra_pages.append((translations["health"], "health.md"))

        patterns = {d.class_id: d for d in detect_patterns(graph)}
        for module in graph.iter_nodes(NodeKind.MODULE):
            slug = page_slug(graph, module.id)
            _write(
                docs / "modules" / f"{slug}.md",
                render_module_page(graph, module.id, config, patterns),
            )
            diagram = render_class_diagram(graph, module.id, config.analysis.include_private)
            if "class " in diagram:  # n'émet un artefact que si le module a des classes
                _write(staging / "diagrams" / f"{slug}.mmd", diagram)

        assets_dir = docs / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        for asset in sorted(_ASSETS.iterdir()):
            shutil.copyfile(asset, assets_dir / asset.name)

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
