"""Complexité cyclomatique — définition commune aux trois langages (ir-schema.md).

complexité = 1 + points de décision : if/elif, boucles, except, expressions
conditionnelles, gardes de compréhension, branches de match, opérandes
supplémentaires des opérateurs booléens court-circuit.
"""

from __future__ import annotations

import ast


class _DecisionCounter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.count = 0

    def visit_If(self, node: ast.If) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.count += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.count += len(node.ifs)
        self.generic_visit(node)

    def visit_match_case(self, node: ast.match_case) -> None:
        self.count += 1
        self.generic_visit(node)

    # Les fonctions/classes imbriquées ont leur propre complexité.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        pass


def cyclomatic_complexity(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Complexité cyclomatique d'une fonction (≥ 1)."""
    counter = _DecisionCounter()
    for statement in function.body:
        counter.visit(statement)
    return 1 + counter.count
