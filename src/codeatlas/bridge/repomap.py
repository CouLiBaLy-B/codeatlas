"""Carte du dépôt (RepoMap) : contexte compact et déterministe pour les assistants IA.

Contrat : specs/003-ai-context-bridge/contracts/bridge.md.
Priorisation : modules portant des points d'entrée, puis fan-in décroissant, puis
ordre alphabétique — un module est inclus en entier ou pas du tout ; toute omission
est explicite. Les résumés proviennent UNIQUEMENT de la documentation existante.
"""

from __future__ import annotations

from codeatlas.config import Config
from codeatlas.insights.entrypoints import detect_entrypoints
from codeatlas.insights.metrics import compute_metrics
from codeatlas.ir.model import CodeGraph, EdgeKind, Node, NodeKind, Visibility

MIN_BUDGET = 2000
_OMITTED_LIST_MAX = 10


def _qualname(node_id: str) -> str:
    return node_id.split("/", 1)[-1]


def _module_priority(graph: CodeGraph) -> list[Node]:
    """Modules ordonnés : points d'entrée d'abord, puis fan-in décroissant, puis alpha."""
    entry_module_ids = set()
    for entry in detect_entrypoints(graph):
        node = graph.get_node(entry.node_id)
        if node is None:
            continue
        if node.kind is NodeKind.MODULE:
            entry_module_ids.add(node.id)
        else:
            entry_module_ids.add(node.id.rsplit(".", 1)[0].rsplit(".", 1)[0])
            # id de méthode → module ; id de fonction → module
            entry_module_ids.add(node.id.rsplit(".", 1)[0])

    fan_in: dict[str, int] = {}
    for edge in graph.edges_of_kind(EdgeKind.IMPORTS):
        fan_in[edge.target] = fan_in.get(edge.target, 0) + 1

    modules = list(graph.iter_nodes(NodeKind.MODULE))
    return sorted(
        modules,
        key=lambda m: (
            m.id not in entry_module_ids,
            -fan_in.get(m.id, 0),
            m.id,
        ),
    )


def _symbol_line(node: Node) -> str:
    summary = f" — {node.doc.summary}" if node.doc else ""
    return f"- `{node.name}{node.signature}`{summary}"


def _module_block(graph: CodeGraph, module: Node) -> str:
    qualname = _qualname(module.id)
    lines = [f"### {qualname}"]
    if module.doc:
        lines.append(f"{module.doc.summary}")
    for kind in (NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM):
        for cls in graph.children_of(module.id, kind):
            if cls.visibility is Visibility.PRIVATE:
                continue
            summary = f" — {cls.doc.summary}" if cls.doc else ""
            lines.append(f"- **{cls.name}**{summary}")
            for method in graph.children_of(cls.id, NodeKind.METHOD):
                if method.visibility is Visibility.PRIVATE:
                    continue
                doc = f" — {method.doc.summary}" if method.doc else ""
                lines.append(f"  - `{method.name}{method.signature}`{doc}")
    for fn in graph.children_of(module.id, NodeKind.FUNCTION):
        if fn.visibility is Visibility.PRIVATE:
            continue
        lines.append(_symbol_line(fn))
    return "\n".join(lines) + "\n"


def _header(graph: CodeGraph, config: Config) -> str:
    from codeatlas.insights.architecture import compute_architecture

    health = compute_metrics(graph, config)
    architecture = compute_architecture(graph)
    modules_count = sum(1 for _ in graph.iter_nodes(NodeKind.MODULE))

    lines = [
        f"# Carte du dépôt : {graph.root}",
        "",
        "> Carte déterministe générée par CodeAtlas (analyse statique, sans LLM) —",
        "> destinée à servir de contexte fiable aux assistants IA.",
        "",
        "## Vue d'ensemble",
        "- Sous-projets : "
        + ", ".join(f"{s.id} ({s.language})" for s in graph.subprojects),
        f"- Modules : {modules_count} · Symboles : {len(graph.nodes)} · "
        f"Couverture doc : {health.global_doc_coverage} %",
    ]
    if architecture.layers:
        layer_text = " · ".join(
            f"{layer.name} : {', '.join(layer.packages)}" for layer in architecture.layers
        )
        lines.append(f"- Couches : {layer_text}")
    if graph.skipped:
        lines.append(f"- Fichiers non analysés : {len(graph.skipped)}")

    entries = detect_entrypoints(graph)
    if entries:
        lines.extend(["", "## Points d'entrée"])
        for entry in entries:
            lines.append(f"- {entry.label} ({entry.framework}) — `{_qualname(entry.node_id)}`")
    return "\n".join(lines) + "\n"


def build_repomap(graph: CodeGraph, config: Config, budget: int | None = None) -> str:
    """Carte markdown ≤ budget caractères — déterministe octet pour octet."""
    limit = budget if budget is not None else config.export.budget
    if limit < MIN_BUDGET:
        raise ValueError(f"budget trop petit : {limit} (minimum {MIN_BUDGET} caractères)")

    header = _header(graph, config)
    tour = _tour_section(graph, config)
    api_heading = "\n## API publique\n\n"

    modules = _module_priority(graph)
    blocks = [(module, _module_block(graph, module)) for module in modules]

    # placeholder maximal de la section d'omission, réservé d'avance
    omitted_reserve = len(_omitted_section([_qualname(m.id) for m, _ in blocks]))

    included: list[str] = []
    omitted: list[str] = []
    used = len(header) + len(tour) + len(api_heading)
    for module, block in blocks:
        candidate = used + len(block) + 1
        if candidate + omitted_reserve <= limit:
            included.append(block)
            used = candidate
        else:
            omitted.append(_qualname(module.id))

    parts = [header, tour, api_heading, "\n".join(included)]
    if omitted:
        parts.append(_omitted_section(omitted))
    text = "".join(parts).rstrip("\n") + "\n"
    if len(text) > limit:  # pragma: no cover — garde-fou
        raise ValueError("dépassement de budget interne")
    return text


def _tour_section(graph: CodeGraph, config: Config) -> str:
    """Section « Parcours de lecture » (US4) — vide tant que l'insight est absent."""
    try:
        from codeatlas.insights.tour import reading_tour
    except ImportError:  # pragma: no cover
        return ""
    steps = reading_tour(graph, config)
    if not steps:
        return ""
    lines = ["", "## Parcours de lecture"]
    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {step.module} ({step.reason})")
    return "\n".join(lines) + "\n"


def _omitted_section(omitted: list[str]) -> str:
    if not omitted:
        return ""
    shown = omitted[:_OMITTED_LIST_MAX]
    more = len(omitted) - len(shown)
    suffix = f" et {more} autre(s)" if more > 0 else ""
    return (
        "\n## Omis (budget)\n"
        f"{len(omitted)} module(s) omis : {', '.join(shown)}{suffix} — "
        "utilisez `codeatlas export --budget N` plus large ou `module_api` via MCP.\n"
    )
