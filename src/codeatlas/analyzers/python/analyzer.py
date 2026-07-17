"""Analyseur Python : `ast` natif → fragment d'IR (adapté du projet gendoc).

Deux passes : (A) parse + inventaire des classes de tous les modules,
(B) extraction des nœuds et arêtes avec résolution des noms importés.
Un fichier invalide devient une entrée `skipped` — jamais une exception
(constitution IV).
"""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from codeatlas.analyzers.base import AnalyzerOptions, IRFragment, SourceFile
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

        # Passe A : parse tolérant + inventaire global.
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

        module_names = {m.qualname for m in modules}
        class_registry = {
            f"{module.qualname}.{stmt.name}"
            for module in modules
            for stmt in module.tree.body
            if isinstance(stmt, ast.ClassDef)
        }

        for module in sorted(modules, key=lambda m: m.qualname):
            _ModuleExtractor(
                module, subproject.id, module_names, class_registry, fragment
            ).extract()

        fragment.nodes.sort(key=lambda n: n.id)
        fragment.edges.sort(key=lambda e: e.key())
        fragment.skipped.sort(key=lambda s: s.path)
        return fragment


class _ModuleExtractor:
    def __init__(
        self,
        module: _ParsedModule,
        subproject_id: str,
        module_names: set[str],
        class_registry: set[str],
        fragment: IRFragment,
    ) -> None:
        self.module = module
        self.sub = subproject_id
        self.module_names = module_names
        self.class_registry = class_registry
        self.fragment = fragment
        self.module_id = f"{subproject_id}/{module.qualname}"
        # alias local → nom qualifié complet du symbole importé
        self.symbol_bindings: dict[str, str] = {}
        self.seen_node_ids: set[str] = set()

    # -- helpers -------------------------------------------------------------

    def _node_id(self, qualname: str) -> str:
        return f"{self.sub}/{qualname}"

    def _add_node(self, node: Node) -> None:
        if node.id not in self.seen_node_ids:
            self.seen_node_ids.add(node.id)
            self.fragment.nodes.append(node)

    def _add_edge(self, source: str, target: str, kind: EdgeKind, line: int) -> None:
        self.fragment.edges.append(
            Edge(
                source=source,
                target=target,
                kind=kind,
                certainty=Certainty.CERTAIN,
                location=Location(file=self.module.path, line=line),
            )
        )

    def _resolve_class(self, expr: ast.expr) -> str | None:
        """Résout une expression vers le nom qualifié d'une classe analysée, sinon None."""
        if isinstance(expr, ast.Name):
            local = f"{self.module.qualname}.{expr.id}"
            if local in self.class_registry:
                return local
            bound = self.symbol_bindings.get(expr.id)
            if bound in self.class_registry:
                return bound
        elif isinstance(expr, ast.Attribute):
            dotted = ast.unparse(expr)
            if dotted in self.class_registry:
                return dotted
        return None

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
        modifiers = frozenset({"package"}) if module.is_package else frozenset()
        self._add_node(
            Node(
                id=self.module_id,
                kind=NodeKind.MODULE,
                name=module.qualname.rsplit(".", 1)[-1],
                subproject=self.sub,
                location=Location(file=module.path, line=1),
                doc=_doc_info(module.tree),
                modifiers=modifiers,
                loc=module.line_count,
            )
        )
        self._extract_imports()
        for statement in module.tree.body:
            if isinstance(statement, ast.ClassDef):
                self._extract_class(statement)
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_function(statement, parent_qual=module.qualname, is_method=False)

    def _extract_imports(self) -> None:
        for node in ast.walk(self.module.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.module_names:
                        self._add_edge(
                            self.module_id,
                            self._node_id(alias.name),
                            EdgeKind.IMPORTS,
                            node.lineno,
                        )
            elif isinstance(node, ast.ImportFrom):
                target = self._resolve_import_from(node)
                if target is None:
                    continue
                for alias in node.names:
                    as_module = f"{target}.{alias.name}"
                    if as_module in self.module_names:
                        # `from pkg import sous_module`
                        self._add_edge(
                            self.module_id,
                            self._node_id(as_module),
                            EdgeKind.IMPORTS,
                            node.lineno,
                        )
                        continue
                    if target in self.module_names:
                        self._add_edge(
                            self.module_id,
                            self._node_id(target),
                            EdgeKind.IMPORTS,
                            node.lineno,
                        )
                        self.symbol_bindings[alias.asname or alias.name] = as_module

    def _resolve_import_from(self, node: ast.ImportFrom) -> str | None:
        if node.level == 0:
            return node.module
        # import relatif : point de départ = package courant
        parts = self.module.qualname.split(".")
        if not self.module.is_package:
            parts = parts[:-1]
        ascend = node.level - 1
        if ascend >= len(parts) and not (ascend == 0 and parts):
            return None
        base = parts[: len(parts) - ascend] if ascend else parts
        if node.module:
            return ".".join((*base, node.module)) if base else node.module
        return ".".join(base) or None

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
                target_id = self._node_id(resolved)
                kind_edge = EdgeKind.INHERITS
                self._add_edge(class_id, target_id, kind_edge, cls.lineno)

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
            name = ast.unparse(decorator).rsplit(".", 1)[-1].split("(")[0]
            if name in ("staticmethod", "classmethod", "property", "abstractmethod"):
                modifiers.add(name)

        self._add_node(
            Node(
                id=self._node_id(f"{parent_qual}.{fn.name}"),
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
