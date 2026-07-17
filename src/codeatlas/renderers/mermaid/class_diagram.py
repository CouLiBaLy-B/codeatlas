"""Renderer Mermaid `classDiagram` d'un module — déterministe, éléments triés."""

from __future__ import annotations

from codeatlas.ir.model import CodeGraph, EdgeKind, Node, NodeKind, Visibility

# ordre de préséance quand plusieurs relations lient la même paire de classes
_RELATION_STRENGTH = {
    EdgeKind.COMPOSES: 3,
    EdgeKind.AGGREGATES: 2,
    EdgeKind.ASSOCIATES: 1,
}
_RELATION_ARROWS = {
    EdgeKind.COMPOSES: "*--",
    EdgeKind.AGGREGATES: "o--",
    EdgeKind.ASSOCIATES: "-->",
}
_KIND_STEREOTYPE = {
    NodeKind.INTERFACE: "<<interface>>",
    NodeKind.ENUM: "<<enumeration>>",
}


def _sanitize(text: str) -> str:
    """Adapte un fragment aux contraintes de syntaxe mermaid (génériques, défauts)."""
    cleaned = text.split(" = ")[0].split("=")[0].strip()
    return cleaned.replace("[", "~").replace("]", "~").replace("|", " / ")


def _member_lines(graph: CodeGraph, cls: Node, include_private: bool) -> list[str]:
    prefix = f"{cls.id}."
    attributes: list[str] = []
    methods: list[str] = []
    for node in graph.iter_nodes():
        if not node.id.startswith(prefix) or "." in node.id.removeprefix(prefix):
            continue
        if node.visibility is Visibility.PRIVATE and not include_private:
            continue
        marker = "-" if node.visibility is Visibility.PRIVATE else "+"
        if node.kind is NodeKind.ATTRIBUTE:
            typed = f": {_sanitize(node.signature)}" if node.signature else ""
            attributes.append(f"        {marker}{node.name}{typed}")
        elif node.kind is NodeKind.METHOD:
            params, _, returns = node.signature.partition(" -> ")
            arg_names = ", ".join(
                part.split(":")[0].strip()
                for part in params.strip("()").split(",")
                if part.strip() and part.strip() not in ("*", "/")
            )
            rendered = f"        {marker}{node.name}({arg_names})"
            if returns:
                rendered += f" {_sanitize(returns)}"
            methods.append(rendered)
    return sorted(attributes) + sorted(methods)


def render_class_diagram(
    graph: CodeGraph, module_id: str, include_private: bool = False
) -> str:
    """Diagramme de classes d'un module (héritage, composition, agrégation, association)."""
    prefix = f"{module_id}."
    classes = [
        node
        for node in graph.iter_nodes()
        if node.kind in (NodeKind.CLASS, NodeKind.INTERFACE, NodeKind.ENUM)
        and node.id.startswith(prefix)
        and "." not in node.id.removeprefix(prefix)
        and (include_private or node.visibility is not Visibility.PRIVATE)
    ]
    lines = ["classDiagram"]
    class_ids = {c.id for c in classes}

    for cls in sorted(classes, key=lambda c: c.name):
        lines.append(f"    class {cls.name} {{")
        stereotype = _KIND_STEREOTYPE.get(cls.kind)
        if stereotype:
            lines.append(f"        {stereotype}")
        lines.extend(_member_lines(graph, cls, include_private))
        lines.append("    }")

    short = {node_id: node_id.rsplit(".", 1)[-1] for node_id in graph.nodes}

    inheritance: list[str] = []
    for edge in graph.edges_of_kind(EdgeKind.INHERITS, EdgeKind.IMPLEMENTS):
        if edge.source in class_ids or edge.target in class_ids:
            arrow = "<|.." if edge.kind is EdgeKind.IMPLEMENTS else "<|--"
            inheritance.append(f"    {short[edge.target]} {arrow} {short[edge.source]}")

    strongest: dict[tuple[str, str], EdgeKind] = {}
    for edge in graph.edges_of_kind(EdgeKind.COMPOSES, EdgeKind.AGGREGATES, EdgeKind.ASSOCIATES):
        if edge.source not in class_ids:
            continue
        pair = (edge.source, edge.target)
        current = strongest.get(pair)
        if current is None or _RELATION_STRENGTH[edge.kind] > _RELATION_STRENGTH[current]:
            strongest[pair] = edge.kind

    relations = [
        f"    {short[source]} {_RELATION_ARROWS[kind]} {short[target]}"
        for (source, target), kind in sorted(strongest.items())
    ]
    lines.extend(sorted(inheritance))
    lines.extend(relations)
    return "\n".join(lines) + "\n"
