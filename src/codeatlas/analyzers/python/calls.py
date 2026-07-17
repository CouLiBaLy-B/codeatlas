"""Extraction des appels (arêtes `calls`) avec certitude honnête (R6, FR-009).

Résolution statique bornée et transparente :
- `certain` : fonction locale/importée nommément, constructeur, méthode atteinte via
  une chaîne de types DÉCLARÉS (self, paramètres annotés, attributs typés, variables
  locales ou de module affectées depuis un constructeur) ;
- `inferred` : `getattr(obj, "literal")` dont la cible est résolue par nom ;
- tout le reste est ignoré (jamais de fausse certitude).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from codeatlas.ir.model import Certainty


@dataclass(slots=True)
class ClassInfo:
    qualname: str
    methods: set[str] = field(default_factory=set)
    attr_types: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class GlobalContext:
    """Inventaire global du sous-projet, construit avant l'extraction des arêtes."""

    module_names: set[str] = field(default_factory=set)
    class_registry: set[str] = field(default_factory=set)
    function_registry: set[str] = field(default_factory=set)
    class_infos: dict[str, ClassInfo] = field(default_factory=dict)
    module_bindings: dict[str, dict[str, str]] = field(default_factory=dict)
    module_var_types: dict[str, dict[str, str]] = field(default_factory=dict)


def resolve_class_name(
    expr: ast.expr, module_qualname: str, bindings: dict[str, str], class_registry: set[str]
) -> str | None:
    """Résout une expression (Name/Attribute) vers une classe analysée, sinon None."""
    if isinstance(expr, ast.Name):
        local = f"{module_qualname}.{expr.id}"
        if local in class_registry:
            return local
        bound = bindings.get(expr.id)
        if bound in class_registry:
            return bound
    elif isinstance(expr, ast.Attribute):
        dotted = ast.unparse(expr)
        if dotted in class_registry:
            return dotted
    return None


def annotation_class(
    annotation: ast.expr,
    module_qualname: str,
    bindings: dict[str, str],
    class_registry: set[str],
) -> str | None:
    """Première classe analysée référencée dans une annotation (`X`, `X | None`…)."""
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name):
            resolved = resolve_class_name(node, module_qualname, bindings, class_registry)
            if resolved is not None:
                return resolved
    return None


class CallExtractor:
    """Extrait les appels d'une fonction/méthode donnée."""

    def __init__(
        self,
        ctx: GlobalContext,
        module_qualname: str,
        current_class: str | None,
        fn: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self.ctx = ctx
        self.module = module_qualname
        self.current_class = current_class
        self.fn = fn
        self.bindings = ctx.module_bindings.get(module_qualname, {})
        self.param_types: dict[str, str] = {}
        self.local_types: dict[str, str] = {}

    # -- types ----------------------------------------------------------------

    def _annotation_class(self, annotation: ast.expr) -> str | None:
        return annotation_class(annotation, self.module, self.bindings, self.ctx.class_registry)

    def _collect_param_types(self) -> None:
        args = self.fn.args
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            if arg.annotation is not None:
                resolved = self._annotation_class(arg.annotation)
                if resolved is not None:
                    self.param_types[arg.arg] = resolved

    def _collect_local_types(self) -> None:
        for node in self._walk_body():
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                resolved = resolve_class_name(
                    node.value.func, self.module, self.bindings, self.ctx.class_registry
                )
                if resolved is not None:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.local_types[target.id] = resolved
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                resolved = self._annotation_class(node.annotation)
                if resolved is not None:
                    self.local_types[node.target.id] = resolved

    def _expr_type(self, expr: ast.expr) -> str | None:
        """Type déclaré d'une expression, si une chaîne de déclarations le prouve."""
        if isinstance(expr, ast.Name):
            if expr.id == "self" and self.current_class is not None:
                return self.current_class
            return (
                self.local_types.get(expr.id)
                or self.param_types.get(expr.id)
                or self.ctx.module_var_types.get(self.module, {}).get(expr.id)
            )
        if isinstance(expr, ast.Attribute):
            owner = self._expr_type(expr.value)
            if owner is not None:
                info = self.ctx.class_infos.get(owner)
                if info is not None:
                    return info.attr_types.get(expr.attr)
            return None
        if isinstance(expr, ast.Call):
            return resolve_class_name(
                expr.func, self.module, self.bindings, self.ctx.class_registry
            )
        return None

    # -- extraction -------------------------------------------------------------

    def _walk_body(self) -> list[ast.AST]:
        """Parcourt le corps en excluant les fonctions/classes imbriquées."""
        collected: list[ast.AST] = []
        stack: list[ast.AST] = list(self.fn.body)
        while stack:
            node = stack.pop()
            collected.append(node)
            for child in ast.iter_child_nodes(node):
                if not isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    stack.append(child)
        return collected

    def _resolve_callable(self, call: ast.Call) -> tuple[str, Certainty] | None:
        func = call.func
        # getattr(obj, "literal") → cible inférée
        if (
            isinstance(func, ast.Name)
            and func.id == "getattr"
            and len(call.args) >= 2
            and isinstance(call.args[1], ast.Constant)
            and isinstance(call.args[1].value, str)
        ):
            owner = self._expr_type(call.args[0])
            method = call.args[1].value
            if owner is not None and method in self.ctx.class_infos[owner].methods:
                return f"{owner}.{method}", Certainty.INFERRED
            return None

        if isinstance(func, ast.Name):
            local = f"{self.module}.{func.id}"
            if local in self.ctx.function_registry:
                return local, Certainty.CERTAIN
            bound = self.bindings.get(func.id)
            if bound is not None and bound in self.ctx.function_registry:
                return bound, Certainty.CERTAIN
            constructor = resolve_class_name(
                func, self.module, self.bindings, self.ctx.class_registry
            )
            if constructor is not None and f"{constructor}.__init__" in self.ctx.function_registry:
                return f"{constructor}.__init__", Certainty.CERTAIN
            return None

        if isinstance(func, ast.Attribute):
            owner = self._expr_type(func.value)
            if owner is not None:
                info = self.ctx.class_infos.get(owner)
                if info is not None and func.attr in info.methods:
                    return f"{owner}.{func.attr}", Certainty.CERTAIN
        return None

    def extract(self) -> list[tuple[str, Certainty, int]]:
        """Liste triée de (cible, certitude, ligne) des appels résolus."""
        self._collect_param_types()
        self._collect_local_types()
        results: set[tuple[str, str, int]] = set()
        for node in self._walk_body():
            if isinstance(node, ast.Call):
                resolved = self._resolve_callable(node)
                if resolved is not None:
                    target, certainty = resolved
                    results.add((target, certainty.value, node.lineno))
        return sorted(
            (target, Certainty(certainty), line) for target, certainty, line in results
        )
