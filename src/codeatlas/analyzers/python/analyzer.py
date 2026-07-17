"""Analyseur Python : `ast` natif → fragment d'IR (adapté du projet gendoc).

Passes : (A) parse tolérant ; (B) inventaire global — modules, classes, fonctions,
imports/bindings, types d'attributs et de variables de module ; (C) extraction des
nœuds et arêtes, dont les appels (`calls.py`).
Un fichier invalide devient une entrée `skipped` — jamais une exception
(constitution IV).
"""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from codeatlas.analyzers.base import AnalyzerOptions, IRFragment, SourceFile
from codeatlas.analyzers.python.calls import (
    CallExtractor,
    ClassInfo,
    GlobalContext,
    annotation_class,
    resolve_class_name,
)
from codeatlas.analyzers.python.complexity import cyclomatic_complexity
from codeatlas.ir.model import (
    Certainty,
    DocFormat,
    DocInfo,
    Edge,
    EdgeKind,
    Location,
    Node,
    NodeKind,
    SkippedFile,
    SubProject,
    Visibility,
)

_INTERFACE_BASES = {"Protocol", "ABC", "ABCMeta"}
_ENUM_BASES = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}


def module_qualname(posix_path: str) -> tuple[str, bool]:
    """`pkg/mod.py` → (`pkg.mod`, False) ; `pkg/__init__.py` → (`pkg`, True)."""
    parts = posix_path.removesuffix(".py").split("/")
    if parts[-1] == "__init__":
        return ".".join(parts[:-1]) or parts[0], True
    return ".".join(parts), False


def _visibility(name: str) -> Visibility:
    if name.startswith("__") and name.endswith("__"):
        return Visibility.PUBLIC  # dunder = API du langage
    return Visibility.PRIVATE if name.startswith("_") else Visibility.PUBLIC


def _doc_info(
    node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> DocInfo | None:
    raw = ast.get_docstring(node)
    if not raw:
        return None
    summary = next((line.strip() for line in raw.splitlines() if line.strip()), "")
    return DocInfo(raw=raw, summary=summary, format=DocFormat.DOCSTRING)


def _loc(node: ast.stmt) -> int:
    end = getattr(node, "end_lineno", None) or node.lineno
    return end - node.lineno + 1


def _is_main_guard(test: ast.expr) -> bool:
    """Reconnaît `__name__ == "__main__"` (dans les deux sens)."""
    if not (isinstance(test, ast.Compare) and len(test.comparators) == 1):
        return False
    operands = [test.left, test.comparators[0]]
    has_name = any(isinstance(op, ast.Name) and op.id == "__name__" for op in operands)
    has_main = any(
        isinstance(op, ast.Constant) and op.value == "__main__" for op in operands
    )
    return has_name and has_main


def _format_signature(fn: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> str:
    args = fn.args
    rendered: list[str] = []

    positional = [*args.posonlyargs, *args.args]
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults))
    defaults.extend(args.defaults)

    for index, (arg, default) in enumerate(zip(positional, defaults, strict=True)):
        if is_method and index == 0 and arg.arg in ("self", "cls"):
            continue
        piece = arg.arg
        if arg.annotation is not None:
            piece += f": {ast.unparse(arg.annotation)}"
        if default is not None:
            piece += f" = {ast.unparse(default)}" if arg.annotation else f"={ast.unparse(default)}"
        rendered.append(piece)
        if args.posonlyargs and index == len(args.posonlyargs) - 1:
            rendered.append("/")

    if args.vararg is not None:
        piece = f"*{args.vararg.arg}"
        if args.vararg.annotation is not None:
            piece += f": {ast.unparse(args.vararg.annotation)}"
        rendered.append(piece)
    elif args.kwonlyargs:
        rendered.append("*")

    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        piece = arg.arg
        if arg.annotation is not None:
            piece += f": {ast.unparse(arg.annotation)}"
        if default is not None:
            piece += f" = {ast.unparse(default)}" if arg.annotation else f"={ast.unparse(default)}"
        rendered.append(piece)

    if args.kwarg is not None:
        piece = f"**{args.kwarg.arg}"
        if args.kwarg.annotation is not None:
            piece += f": {ast.unparse(args.kwarg.annotation)}"
        rendered.append(piece)

    signature = f"({', '.join(rendered)})"
    if fn.returns is not None:
        signature += f" -> {ast.unparse(fn.returns)}"
    return signature


@dataclass(slots=True)
class _ParsedModule:
    path: str
    qualname: str
    is_package: bool
    tree: ast.Module
    line_count: int
    import_edges: list[tuple[str, int]] = field(default_factory=list)
    bindings: dict[str, str] = field(default_factory=dict)


def _resolve_import_from(module: _ParsedModule, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    # import relatif : point de départ = package courant
    parts = module.qualname.split(".")
    if not module.is_package:
        parts = parts[:-1]
    ascend = node.level - 1
    if ascend > len(parts):
        return None
    base = parts[: len(parts) - ascend] if ascend else parts
    if node.module:
        return ".".join((*base, node.module)) if base else node.module
    return ".".join(base) or None


def _iter_statements(tree: ast.Module) -> list[ast.stmt]:
    """Toutes les instructions du module (sans visiter les expressions — perf)."""
    statements: list[ast.stmt] = []
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        for attr in ("body", "orelse", "finalbody", "handlers", "cases"):
            children = getattr(node, attr, None)
            if children:
                stack.extend(children)
        if isinstance(node, ast.stmt):
            statements.append(node)
    return statements


def _collect_imports(
    module: _ParsedModule, module_names: set[str]
) -> tuple[list[tuple[str, int]], dict[str, str]]:
    """(arêtes d'import vers des modules analysés, alias → symbole qualifié)."""
    edges: list[tuple[str, int]] = []
    bindings: dict[str, str] = {}
    for node in _iter_statements(module.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in module_names:
                    edges.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            target = _resolve_import_from(module, node)
            if target is None:
                continue
            for alias in node.names:
                as_module = f"{target}.{alias.name}"
                if as_module in module_names:
                    edges.append((as_module, node.lineno))
                elif target in module_names:
                    edges.append((target, node.lineno))
                    bindings[alias.asname or alias.name] = as_module
    return edges, bindings


def _init_attr_types(
    init: ast.FunctionDef | ast.AsyncFunctionDef,
    module_q: str,
    bindings: dict[str, str],
    class_registry: set[str],
) -> dict[str, str]:
    """Types déclarés des attributs affectés dans __init__ (self.x = …)."""
    param_types: dict[str, str] = {}
    for arg in (*init.args.posonlyargs, *init.args.args, *init.args.kwonlyargs):
        if arg.annotation is not None:
            param_class = annotation_class(arg.annotation, module_q, bindings, class_registry)
            if param_class is not None:
                param_types[arg.arg] = param_class

    types: dict[str, str] = {}
    for statement in ast.walk(init):
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        annotation: ast.expr | None = None
        if isinstance(statement, ast.Assign):
            targets, value = statement.targets, statement.value
        elif isinstance(statement, ast.AnnAssign):
            targets, value, annotation = [statement.target], statement.value, statement.annotation
        for target in targets:
            if not (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                continue
            resolved: str | None = None
            if annotation is not None:
                resolved = annotation_class(annotation, module_q, bindings, class_registry)
            if resolved is None and isinstance(value, ast.Call):
                resolved = resolve_class_name(value.func, module_q, bindings, class_registry)
            if resolved is None and isinstance(value, ast.Name):
                resolved = param_types.get(value.id)
            if resolved is not None:
                types.setdefault(target.attr, resolved)
    return types


class PythonAnalyzer:
    """Implémente le contrat LanguageAnalyzer pour Python."""

    language: ClassVar[str] = "python"
    extensions: ClassVar[frozenset[str]] = frozenset({".py"})
    manifests: ClassVar[frozenset[str]] = frozenset({"pyproject.toml", "setup.py", "setup.cfg"})

    def analyze(
        self,
        files: Sequence[SourceFile],
        subproject: SubProject,
        options: AnalyzerOptions,
    ) -> IRFragment:
        fragment = IRFragment()
        modules: list[_ParsedModule] = []

        # Passe A : parse tolérant.
        for source in files:
            try:
                tree = ast.parse(source.text)
            except SyntaxError as exc:
                fragment.skipped.append(
                    SkippedFile(
                        path=source.path,
                        reason=f"SyntaxError: {exc.msg} (ligne {exc.lineno})",
                    )
                )
                continue
            except (ValueError, RecursionError) as exc:  # pragma: no cover — rare
                fragment.skipped.append(SkippedFile(path=source.path, reason=repr(exc)))
                continue
            qualname, is_package = module_qualname(source.path)
            modules.append(
                _ParsedModule(
                    path=source.path,
                    qualname=qualname,
                    is_package=is_package,
                    tree=tree,
                    line_count=len(source.text.splitlines()),
                )
            )

        # Passe B : inventaire global.
        ctx = GlobalContext(module_names={m.qualname for m in modules})
        for module in modules:
            module.import_edges, module.bindings = _collect_imports(module, ctx.module_names)
            ctx.module_bindings[module.qualname] = module.bindings

        for module in modules:
            for statement in module.tree.body:
                if isinstance(statement, ast.ClassDef):
                    qual = f"{module.qualname}.{statement.name}"
                    ctx.class_registry.add(qual)
                    info = ClassInfo(qualname=qual)
                    for sub in statement.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            info.methods.add(sub.name)
                            ctx.function_registry.add(f"{qual}.{sub.name}")
                    ctx.class_infos[qual] = info
                elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    ctx.function_registry.add(f"{module.qualname}.{statement.name}")

        for module in modules:
            var_types: dict[str, str] = {}
            for statement in module.tree.body:
                if isinstance(statement, ast.ClassDef):
                    info = ctx.class_infos[f"{module.qualname}.{statement.name}"]
                    for sub in statement.body:
                        if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                            resolved = annotation_class(
                                sub.annotation, module.qualname, module.bindings, ctx.class_registry
                            )
                            if resolved is not None:
                                info.attr_types.setdefault(sub.target.id, resolved)
                        elif (
                            isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and sub.name == "__init__"
                        ):
                            info.attr_types.update(
                                _init_attr_types(
                                    sub, module.qualname, module.bindings, ctx.class_registry
                                )
                            )
                elif isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Call):
                    var_class = resolve_class_name(
                        statement.value.func, module.qualname, module.bindings, ctx.class_registry
                    )
                    if var_class is not None:
                        for target in statement.targets:
                            if isinstance(target, ast.Name):
                                var_types[target.id] = var_class
            if var_types:
                ctx.module_var_types[module.qualname] = var_types

        # Passe C : extraction.
        for module in sorted(modules, key=lambda m: m.qualname):
            _ModuleExtractor(module, subproject.id, ctx, fragment).extract()

        fragment.nodes.sort(key=lambda n: n.id)
        fragment.edges.sort(key=lambda e: e.key())
        fragment.skipped.sort(key=lambda s: s.path)
        return fragment


class _ModuleExtractor:
    def __init__(
        self,
        module: _ParsedModule,
        subproject_id: str,
        ctx: GlobalContext,
        fragment: IRFragment,
    ) -> None:
        self.module = module
        self.sub = subproject_id
        self.ctx = ctx
        self.fragment = fragment
        self.module_id = f"{subproject_id}/{module.qualname}"
        self.seen_node_ids: set[str] = set()

    # -- helpers -------------------------------------------------------------

    def _node_id(self, qualname: str) -> str:
        return f"{self.sub}/{qualname}"

    def _add_node(self, node: Node) -> None:
        if node.id not in self.seen_node_ids:
            self.seen_node_ids.add(node.id)
            self.fragment.nodes.append(node)

    def _add_edge(
        self,
        source: str,
        target: str,
        kind: EdgeKind,
        line: int,
        certainty: Certainty = Certainty.CERTAIN,
    ) -> None:
        self.fragment.edges.append(
            Edge(
                source=source,
                target=target,
                kind=kind,
                certainty=certainty,
                location=Location(file=self.module.path, line=line),
            )
        )

    def _resolve_class(self, expr: ast.expr) -> str | None:
        return resolve_class_name(
            expr, self.module.qualname, self.module.bindings, self.ctx.class_registry
        )

    def _annotation_classes(self, annotation: ast.expr) -> list[str]:
        """Toutes les classes internes référencées dans une annotation (ex. list[X])."""
        found: list[str] = []
        for name in ast.walk(annotation):
            if isinstance(name, ast.Name):
                resolved = self._resolve_class(name)
                if resolved is not None:
                    found.append(resolved)
        return found

    # -- extraction ------------------------------------------------------------

    def extract(self) -> None:
        module = self.module
        modifiers: set[str] = {"package"} if module.is_package else set()
        if any(
            isinstance(stmt, ast.If) and _is_main_guard(stmt.test) for stmt in module.tree.body
        ):
            modifiers.add("main_guard")
        self._add_node(
            Node(
                id=self.module_id,
                kind=NodeKind.MODULE,
                name=module.qualname.rsplit(".", 1)[-1],
                subproject=self.sub,
                location=Location(file=module.path, line=1),
                doc=_doc_info(module.tree),
                modifiers=frozenset(modifiers),
                loc=module.line_count,
            )
        )
        for target, line in module.import_edges:
            self._add_edge(self.module_id, self._node_id(target), EdgeKind.IMPORTS, line)
        for statement in module.tree.body:
            if isinstance(statement, ast.ClassDef):
                self._extract_class(statement)
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_function(statement, parent_qual=module.qualname, is_method=False)

    def _extract_class(self, cls: ast.ClassDef) -> None:
        qualname = f"{self.module.qualname}.{cls.name}"
        class_id = self._node_id(qualname)

        base_names = {ast.unparse(base).rsplit(".", 1)[-1] for base in cls.bases}
        if base_names & _ENUM_BASES:
            kind = NodeKind.ENUM
        elif base_names & _INTERFACE_BASES:
            kind = NodeKind.INTERFACE
        else:
            kind = NodeKind.CLASS

        self._add_node(
            Node(
                id=class_id,
                kind=kind,
                name=cls.name,
                subproject=self.sub,
                location=Location(file=self.module.path, line=cls.lineno),
                visibility=_visibility(cls.name),
                doc=_doc_info(cls),
                loc=_loc(cls),
            )
        )

        for base in cls.bases:
            resolved = self._resolve_class(base)
            if resolved is not None:
                self._add_edge(class_id, self._node_id(resolved), EdgeKind.INHERITS, cls.lineno)

        for statement in cls.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_function(statement, parent_qual=qualname, is_method=True)
                if statement.name == "__init__":
                    self._extract_init_relations(statement, class_id, qualname)
            elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                self._extract_class_attribute(statement, class_id, qualname)

    def _extract_class_attribute(
        self, statement: ast.AnnAssign, class_id: str, class_qual: str
    ) -> None:
        name = statement.target.id  # type: ignore[union-attr]
        self._add_node(
            Node(
                id=self._node_id(f"{class_qual}.{name}"),
                kind=NodeKind.ATTRIBUTE,
                name=name,
                subproject=self.sub,
                location=Location(file=self.module.path, line=statement.lineno),
                visibility=_visibility(name),
                signature=ast.unparse(statement.annotation),
            )
        )
        for target_qual in self._annotation_classes(statement.annotation):
            self._add_edge(
                class_id, self._node_id(target_qual), EdgeKind.ASSOCIATES, statement.lineno
            )

    def _extract_init_relations(
        self, init: ast.FunctionDef | ast.AsyncFunctionDef, class_id: str, class_qual: str
    ) -> None:
        param_types: dict[str, list[str]] = {}
        for arg in (*init.args.posonlyargs, *init.args.args, *init.args.kwonlyargs):
            if arg.annotation is not None:
                param_types[arg.arg] = self._annotation_classes(arg.annotation)

        for statement in ast.walk(init):
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            annotation: ast.expr | None = None
            line = init.lineno
            if isinstance(statement, ast.Assign):
                targets, value, line = statement.targets, statement.value, statement.lineno
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                targets, value = [statement.target], statement.value
                annotation, line = statement.annotation, statement.lineno

            for target in targets:
                if not (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    continue
                attribute_id = self._node_id(f"{class_qual}.{target.attr}")
                self._add_node(
                    Node(
                        id=attribute_id,
                        kind=NodeKind.ATTRIBUTE,
                        name=target.attr,
                        subproject=self.sub,
                        location=Location(file=self.module.path, line=line),
                        visibility=_visibility(target.attr),
                        signature=ast.unparse(annotation) if annotation is not None else "",
                    )
                )
                if annotation is not None:
                    for target_qual in self._annotation_classes(annotation):
                        self._add_edge(
                            class_id, self._node_id(target_qual), EdgeKind.ASSOCIATES, line
                        )
                if isinstance(value, ast.Call):
                    resolved = self._resolve_class(value.func)
                    if resolved is not None:
                        self._add_edge(class_id, self._node_id(resolved), EdgeKind.COMPOSES, line)
                elif isinstance(value, ast.Name) and value.id in param_types:
                    for target_qual in param_types[value.id]:
                        self._add_edge(
                            class_id, self._node_id(target_qual), EdgeKind.AGGREGATES, line
                        )

    def _extract_function(
        self,
        fn: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_qual: str,
        is_method: bool,
    ) -> None:
        modifiers: set[str] = set()
        if isinstance(fn, ast.AsyncFunctionDef):
            modifiers.add("async")
        for decorator in fn.decorator_list:
            unparsed = ast.unparse(decorator)
            modifiers.add(f"decorator:{unparsed}")
            name = unparsed.rsplit(".", 1)[-1].split("(")[0]
            if name in ("staticmethod", "classmethod", "property", "abstractmethod"):
                modifiers.add(name)

        fn_id = self._node_id(f"{parent_qual}.{fn.name}")
        self._add_node(
            Node(
                id=fn_id,
                kind=NodeKind.METHOD if is_method else NodeKind.FUNCTION,
                name=fn.name,
                subproject=self.sub,
                location=Location(file=self.module.path, line=fn.lineno),
                visibility=_visibility(fn.name),
                signature=_format_signature(fn, is_method),
                doc=_doc_info(fn),
                modifiers=frozenset(modifiers),
                complexity=cyclomatic_complexity(fn),
                loc=_loc(fn),
            )
        )
        extractor = CallExtractor(
            self.ctx,
            self.module.qualname,
            parent_qual if is_method else None,
            fn,
        )
        for target_qual, certainty, line in extractor.extract():
            self._add_edge(fn_id, self._node_id(target_qual), EdgeKind.CALLS, line, certainty)
