"""Utilitaires communs aux analyseurs tree-sitter (JS/TS, Java)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from codeatlas.ir.model import DocFormat, DocInfo

if TYPE_CHECKING:  # pragma: no cover
    from tree_sitter import Node as TSNode


def text(node: TSNode) -> str:
    return (node.text or b"").decode("utf-8", errors="replace")


def descendants(node: TSNode, types: frozenset[str]) -> Iterator[TSNode]:
    """Descendants (préfixe, déterministe) dont le type appartient à `types`."""
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in types:
            yield current
        stack.extend(reversed(current.named_children))


def count_complexity(body: TSNode, decision_types: frozenset[str]) -> int:
    """Complexité cyclomatique : 1 + points de décision (même définition partout)."""
    count = 1
    stack = list(body.named_children)
    while stack:
        node = stack.pop()
        if node.type in decision_types:
            count += 1
        elif node.type == "binary_expression":
            operator = node.child_by_field_name("operator")
            if operator is not None and text(operator) in ("&&", "||", "??"):
                count += 1
        # les fonctions imbriquées ont leur propre complexité
        if node.type not in (
            "function_declaration",
            "method_definition",
            "method_declaration",
            "class_declaration",
        ):
            stack.extend(node.named_children)
    return count


def doc_comment(statement: TSNode, doc_format: DocFormat) -> DocInfo | None:
    """Commentaire de documentation `/** … */` précédant immédiatement un nœud."""
    sibling = statement.prev_named_sibling
    if sibling is None or sibling.type not in ("comment", "block_comment"):
        return None
    raw_text = text(sibling)
    if not raw_text.startswith("/**"):
        return None
    lines = []
    for line in raw_text.removeprefix("/**").removesuffix("*/").splitlines():
        cleaned = line.strip().lstrip("*").strip()
        if cleaned:
            lines.append(cleaned)
    if not lines:
        return None
    return DocInfo(raw="\n".join(lines), summary=lines[0], format=doc_format)


def line_of(node: TSNode) -> int:
    return node.start_point[0] + 1


def loc_of(node: TSNode) -> int:
    return node.end_point[0] - node.start_point[0] + 1
