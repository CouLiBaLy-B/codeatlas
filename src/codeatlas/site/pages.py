"""Préparation des pages du site depuis l'IR, rendues par les templates Jinja2."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from codeatlas.config import Config
from codeatlas.graph.algorithms import package_cycles
from codeatlas.insights.architecture import compute_architecture
from codeatlas.insights.deadcode import find_dead_code
from codeatlas.insights.entrypoints import detect_entrypoints
from codeatlas.insights.metrics import STATUS_CRITICAL, STATUS_WARN, compute_metrics
from codeatlas.insights.patterns import PatternDetection, detect_patterns
from codeatlas.ir.model import CodeGraph, Node, NodeKind, Visibility
from codeatlas.renderers.mermaid.architecture import render_architecture
from codeatlas.renderers.mermaid.call_flow import render_call_flow
from codeatlas.renderers.mermaid.class_diagram import render_class_diagram
from codeatlas.renderers.mermaid.package_deps import render_package_deps
from codeatlas.site.i18n import labels


@lru_cache(maxsize=1)
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
    )


def _visible(node: Node, config: Config) -> bool:
    return config.analysis.include_private or node.visibility is not Visibility.PRIVATE


def _children(graph: CodeGraph, parent_id: str, kind: NodeKind) -> list[Node]:
    return graph.children_of(parent_id, kind)


def _class_context(
    graph: CodeGraph,
    cls: Node,
    config: Config,
    patterns: dict[str, PatternDetection] | None = None,
) -> dict[str, Any]:
    detection = (patterns or {}).get(cls.id)
    return {
        "name": cls.name,
        "doc": cls.doc.raw if cls.doc else "",
        "file": cls.location.file,
        "line": cls.location.line,
        "pattern": detection.pattern if detection else "",
        "pattern_evidence": list(detection.evidence) if detection else [],
        "attributes": [
            {"name": a.name, "type": a.signature}
            for a in _children(graph, cls.id, NodeKind.ATTRIBUTE)
            if _visible(a, config)
        ],
        "methods": [
            {
                "name": m.name,
                "signature": m.signature,
                "summary": m.doc.summary if m.doc else "",
            }
            for m in _children(graph, cls.id, NodeKind.METHOD)
            if _visible(m, config)
        ],
    }


def build_relations_index(graph: CodeGraph) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Appelants/appelés par symbole, précalculés UNE fois par build (performance).

    Chaque entrée est cliquable (page + ancre) et conserve la certitude (FR-017).
    """
    from codeatlas.ir.model import EdgeKind

    modules_desc = sorted(
        (m.id for m in graph.iter_nodes(NodeKind.MODULE)), key=lambda i: -len(i)
    )

    def _href(node: Node) -> str:
        # Ces liens sont rendus SUR des pages de modules (docs/modules/<slug>.md) :
        # la cible est une page sœur, donc chemin relatif nu, sans préfixe `modules/`
        # (sinon mkdocs résout vers `modules/modules/<slug>.md`, lien cassé).
        owner = next((m for m in modules_desc if node.id.startswith(f"{m}.")), None)
        if owner is None:
            return ""
        href = f"{page_slug(graph, owner)}.md"
        if node.kind in (NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM, NodeKind.FUNCTION):
            return f"{href}#{node.name.lower()}"
        if node.kind is NodeKind.METHOD:
            owner_class = node.id.rsplit(".", 2)[-2]
            return f"{href}#{owner_class.lower()}"
        return href

    href_cache: dict[str, str] = {}
    index: dict[str, dict[str, list[dict[str, Any]]]] = {}

    def _entry(other_id: str, certain: bool) -> dict[str, Any] | None:
        node = graph.get_node(other_id)
        if node is None:
            return None
        if other_id not in href_cache:
            href_cache[other_id] = _href(node)
        return {
            "qualname": _qualname(other_id),
            "href": href_cache[other_id],
            "certain": certain,
        }

    for edge in graph.edges_of_kind(EdgeKind.CALLS):
        certain = edge.certainty.value == "certain"
        caller_entry = _entry(edge.source, certain)
        callee_entry = _entry(edge.target, certain)
        if callee_entry is not None:
            slot = index.setdefault(edge.source, {"callers": [], "callees": []})
            slot["callees"].append(callee_entry)
        if caller_entry is not None:
            slot = index.setdefault(edge.target, {"callers": [], "callees": []})
            slot["callers"].append(caller_entry)
    for slots in index.values():
        slots["callers"].sort(key=lambda entry: entry["qualname"])
        slots["callees"].sort(key=lambda entry: entry["qualname"])
    return index


def render_module_page(
    graph: CodeGraph,
    module_id: str,
    config: Config,
    patterns: dict[str, PatternDetection] | None = None,
    *,
    explorer: bool = False,
    source_root: Path | None = None,
    relations: dict[str, dict[str, list[dict[str, Any]]]] | None = None,
) -> str:
    """Page markdown d'un module : diagramme, référence API, source et relations."""
    module = graph.get_node(module_id)
    if module is None or module.kind is not NodeKind.MODULE:
        raise ValueError(f"module inconnu : {module_id}")
    if patterns is None:
        patterns = {d.class_id: d for d in detect_patterns(graph)}
    if explorer and relations is None:
        relations = build_relations_index(graph)
    no_relations: dict[str, list[dict[str, Any]]] = {"callers": [], "callees": []}
    translations = labels(config.project.language)

    include_source = (
        explorer and config.explorer.include_source and source_root is not None
    )

    def _excerpt(node: Node) -> dict[str, Any]:
        """Contexte source d'un symbole : extrait exact ou mention explicite."""
        if not include_source:
            return {"excerpt": None, "source_missing": False}
        from codeatlas.explorer.source import extract_excerpt

        assert source_root is not None
        excerpt = extract_excerpt(source_root, node)
        if excerpt is None:
            return {"excerpt": None, "source_missing": True}
        return {
            "excerpt": {
                "path": excerpt.path,
                "start_line": excerpt.start_line,
                "end_line": excerpt.end_line,
                "code": excerpt.code,
            },
            "source_missing": False,
        }

    classes = [
        cls
        for kind in (NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM)
        for cls in _children(graph, module_id, kind)
        if _visible(cls, config)
    ]
    classes.sort(key=lambda c: c.name)
    functions = [
        fn for fn in _children(graph, module_id, NodeKind.FUNCTION) if _visible(fn, config)
    ]

    class_contexts = []
    for cls in classes:
        context = _class_context(graph, cls, config, patterns)
        context.update(_excerpt(cls) if explorer else {"excerpt": None, "source_missing": False})
        if explorer and relations is not None:
            for method_context, method in zip(
                context["methods"],
                [m for m in _children(graph, cls.id, NodeKind.METHOD) if _visible(m, config)],
                strict=False,
            ):
                method_context.update(relations.get(method.id, no_relations))
        class_contexts.append(context)

    function_contexts = []
    for fn in sorted(functions, key=lambda f: f.name):
        fn_context: dict[str, Any] = {
            "name": fn.name,
            "signature": fn.signature,
            "summary": fn.doc.summary if fn.doc else "",
            "callers": [],
            "callees": [],
            "excerpt": None,
            "source_missing": False,
        }
        if explorer:
            if relations is not None:
                fn_context.update(relations.get(fn.id, no_relations))
            fn_context.update(_excerpt(fn))
        function_contexts.append(fn_context)

    languages = {sub.id: sub.language for sub in graph.subprojects}
    qualname = module_id.split("/", 1)[1] if "/" in module_id else module_id
    diagram = (
        render_class_diagram(graph, module_id, config.analysis.include_private)
        if classes
        else ""
    )
    rendered = _environment().get_template("module.md.j2").render(
        t=translations,
        explorer=explorer,
        lang=languages.get(module.subproject, ""),
        module={"qualname": qualname, "doc": module.doc.raw if module.doc else ""},
        class_diagram=diagram,
        classes=class_contexts,
        functions=function_contexts,
    )
    return rendered.rstrip("\n") + "\n"


def _entrypoint_flow_root(graph: CodeGraph, node_id: str) -> str | None:
    """Racine du diagramme de flux d'un point d'entrée (fonction `main` d'un module)."""
    node = graph.get_node(node_id)
    if node is None:
        return None
    if node.kind in (NodeKind.FUNCTION, NodeKind.METHOD):
        return node_id
    if node.kind is NodeKind.MODULE and graph.get_node(f"{node_id}.main") is not None:
        return f"{node_id}.main"
    return None


def render_entrypoints_page(graph: CodeGraph, config: Config) -> str | None:
    """Page « Points d'entrée » avec un flux d'appels par entrée ; None si aucune."""
    entries = detect_entrypoints(graph)
    if not entries:
        return None
    contexts = []
    for entry in entries:
        root = _entrypoint_flow_root(graph, entry.node_id)
        contexts.append(
            {
                "label": entry.label,
                "framework": entry.framework,
                "evidence": entry.evidence,
                "diagram": (
                    render_call_flow(graph, root, config.graphs.call_depth) if root else ""
                ),
            }
        )
    rendered = _environment().get_template("entrypoints.md.j2").render(
        t=labels(config.project.language), entrypoints=contexts
    )
    return rendered.rstrip("\n") + "\n"


_STATUS_ICONS = {STATUS_CRITICAL: "🔴", STATUS_WARN: "⚠️"}


def _qualname(node_id: str) -> str:
    return node_id.split("/", 1)[-1]


def page_slug(graph: CodeGraph, module_id: str) -> str:
    """Nom de fichier de la page d'un module — préfixé en mode monorepo."""
    if len(graph.subprojects) > 1:
        return module_id.replace("/", ".")
    return _qualname(module_id)


def module_display_name(graph: CodeGraph, module_id: str) -> str:
    """Nom affiché d'un module — préfixé par le sous-projet en mode monorepo."""
    if len(graph.subprojects) > 1:
        return module_id.replace("/", ".")
    return _qualname(module_id)


def render_health_page(
    graph: CodeGraph, config: Config, dashboard: dict[str, Any] | None = None
) -> str:
    """Page « Santé du code » : métriques par module, treemap, code mort, ignorés."""
    health = compute_metrics(graph, config)
    dead = find_dead_code(graph)
    treemap_svg = ""
    if dashboard is not None:
        from codeatlas.explorer.dashboard import render_treemap_svg

        subproject_of = {row["id"]: row["subproject"] for row in dashboard["rows"]}
        treemap_svg = render_treemap_svg(dashboard["treemap"], subproject_of)
    rendered = _environment().get_template("health.md.j2").render(
        t=labels(config.project.language),
        treemap_svg=treemap_svg,
        skipped=[{"path": s.path, "reason": s.reason} for s in graph.skipped],
        global_doc_coverage=health.global_doc_coverage,
        modules=[
            {
                "qualname": module_display_name(graph, row.module_id),
                "page": page_slug(graph, row.module_id),
                "loc": row.loc,
                "max_complexity": row.max_complexity,
                "doc_coverage": row.doc_coverage,
                "fan_in": row.fan_in,
                "fan_out": row.fan_out,
                "icon": _STATUS_ICONS.get(row.status, "✅"),
            }
            for row in health.modules
        ],
        worst_functions=[
            {
                "qualname": _qualname(fn.node_id),
                "value": fn.value,
                "icon": _STATUS_ICONS.get(fn.status, "✅"),
            }
            for fn in health.worst_functions
        ],
        dead_code=[
            {
                "qualname": _qualname(entry.node_id),
                "confidence": entry.confidence,
                "reason": entry.reason,
            }
            for entry in dead
        ],
    )
    return rendered.rstrip("\n") + "\n"


def _explorer_labels_json(translations: dict[str, str]) -> str:
    """Libellés passés au JS de l'explorateur — JSON canonique (déterminisme)."""
    from codeatlas.explorer.emit import canonical_json

    return canonical_json(
        {
            "language": translations["language"],
            "layer": translations["layer"],
            "subproject": translations["subproject"],
            "all": translations["all"],
            "hint": translations["explorer_hint"],
            "expand": translations["expand"],
            "collapse": translations["collapse"],
            "open_page": translations["open_page"],
            "deps_in": translations["deps_in"],
            "deps_out": translations["deps_out"],
            "loc": translations["loc"],
            "complexity": translations["complexity"],
            "doc_coverage": translations["doc_coverage"],
            "fan_in": translations["fan_in"],
            "fan_out": translations["fan_out"],
            "modules": translations["modules_count"],
        }
    )


def render_architecture_page(
    graph: CodeGraph, config: Config, explorer: bool = False
) -> str | None:
    """Page « Architecture » : explorateur (si activé), couches, violations, patterns.

    Sans explorateur, None si rien à montrer (comportement historique) ; avec
    explorateur, la page existe toujours — le contenu statique reste le repli FR-005.
    """
    report = compute_architecture(graph)
    patterns = detect_patterns(graph)
    if not explorer and not report.layers and not patterns:
        return None
    pattern_contexts = []
    for detection in patterns:
        module_id = detection.class_id.rsplit(".", 1)[0]
        pattern_contexts.append(
            {
                "pattern": detection.pattern,
                "qualname": _qualname(detection.class_id),
                "page": page_slug(graph, module_id),
                "evidence": list(detection.evidence),
            }
        )
    translations = labels(config.project.language)
    rendered = _environment().get_template("architecture.md.j2").render(
        t=translations,
        explorer_labels=_explorer_labels_json(translations) if explorer else "",
        diagram=render_architecture(graph, report) if report.layers else "",
        fallback_diagram=render_package_deps(graph) if not report.layers else "",
        violations=[
            {
                "source": v.source_package,
                "target": v.target_package,
                "evidence": list(v.evidence),
            }
            for v in report.violations
        ],
        patterns=pattern_contexts,
    )
    return rendered.rstrip("\n") + "\n"


def render_monorepo_page(graph: CodeGraph, config: Config) -> str | None:
    """Page « Monorepo » : graphe inter-services + table des sous-projets."""
    from codeatlas.analyzers.base import available_analyzers
    from codeatlas.renderers.mermaid.services import render_services

    subprojects = graph.subprojects
    if len(subprojects) <= 1:
        return None
    translations = labels(config.project.language)
    supported = set(available_analyzers())
    module_counts: dict[str, int] = {}
    for module in graph.iter_nodes(NodeKind.MODULE):
        module_counts[module.subproject] = module_counts.get(module.subproject, 0) + 1
    rendered = _environment().get_template("monorepo.md.j2").render(
        t=translations,
        diagram=render_services(graph),
        subprojects=[
            {
                "id": sub.id,
                "language": sub.language,
                "files": module_counts.get(sub.id, 0),
                "note": "" if sub.language in supported else translations["unsupported"],
            }
            for sub in subprojects
        ],
    )
    return rendered.rstrip("\n") + "\n"


def render_tour_page(graph: CodeGraph, config: Config) -> str | None:
    """Page « Parcours de lecture » (feature 003) ; None si moins de 2 modules."""
    from codeatlas.insights.tour import reading_tour

    steps = reading_tour(graph, config)
    if len(steps) < 2:
        return None
    rendered = _environment().get_template("tour.md.j2").render(
        t=labels(config.project.language), steps=steps
    )
    return rendered.rstrip("\n") + "\n"


def render_changelog_page(source_root: Path, config: Config) -> str | None:
    """Page « Changelog architectural » depuis .codeatlas/history/ ; None si vide."""
    from codeatlas.baseline.compare import compare
    from codeatlas.baseline.render import render_markdown_body
    from codeatlas.baseline.store import list_archives

    archives = list_archives(source_root)
    if not archives:
        return None
    translations = labels(config.project.language)
    entries = []
    for index, (label, current) in enumerate(archives):
        if index == 0:
            body = translations["initial_state"]
        else:
            body = render_markdown_body(compare(archives[index - 1][1], current)).rstrip("\n")
        entries.append({"label": label, "body": body})
    entries.reverse()  # plus récent en premier
    rendered = _environment().get_template("changelog.md.j2").render(
        t=translations, entries=entries
    )
    return rendered.rstrip("\n") + "\n"


def render_index_page(graph: CodeGraph, config: Config) -> str:
    """Page d'accueil : statistiques, dépendances de packages, cycles, ignorés."""
    translations = labels(config.project.language)
    edges = graph.edges
    rendered = _environment().get_template("index.md.j2").render(
        t=translations,
        title=config.project.title or graph.root,
        stats={
            "files_analyzed": sum(1 for _ in graph.iter_nodes(NodeKind.MODULE)),
            "files_skipped": len(graph.skipped),
            "symbols": len(graph.nodes),
            "relations": len(edges),
        },
        package_diagram=render_package_deps(graph),
        cycles=package_cycles(graph),
        skipped=[{"path": s.path, "reason": s.reason} for s in graph.skipped],
    )
    return rendered.rstrip("\n") + "\n"
