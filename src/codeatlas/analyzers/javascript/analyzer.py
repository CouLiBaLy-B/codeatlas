"""Analyseur JavaScript/TypeScript : tree-sitter → fragment d'IR (R1).

Extraction v1 : modules, classes/interfaces/enums, méthodes/champs, fonctions,
héritage/implémentation, imports relatifs, JSDoc, complexité, visibilité,
enregistrements de routes express (`app.get('/x', …)`) comme modifiers de module.
Les graphes d'appels JS sont hors périmètre v1 (documenté dans le plan).
"""

from __future__ import annotations

import posixpath
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from codeatlas.analyzers._treesitter import (
    count_complexity,
    descendants,
    doc_comment,
    line_of,
    loc_of,
    text,
)
from codeatlas.analyzers.base import AnalyzerOptions, IRFragment, SourceFile
from codeatlas.ir.model import (
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

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

    from tree_sitter import Language as TSLanguage
    from tree_sitter import Node as TSNode

_DECISIONS = frozenset(
    {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "ternary_expression",
        "switch_case",
    }
)
_ROUTE_VERBS = frozenset({"get", "post", "put", "delete", "patch"})
_ROUTE_OBJECTS = frozenset({"app", "router", "server", "api"})
_CLASS_TYPES = frozenset({"class_declaration", "abstract_class_declaration"})


def _doc_anchor(node: TSNode) -> TSNode:
    """Le commentaire JSDoc précède l'`export_statement` quand il y en a un."""
    parent = node.parent
    if parent is not None and parent.type == "export_statement":
        return parent
    return node


def _language_for(path: str) -> TSLanguage:
    from tree_sitter import Language

    if path.endswith((".ts", ".mts", ".cts")):
        import tree_sitter_typescript

        return Language(tree_sitter_typescript.language_typescript())
    if path.endswith(".tsx"):
        import tree_sitter_typescript

        return Language(tree_sitter_typescript.language_tsx())
    import tree_sitter_javascript

    return Language(tree_sitter_javascript.language())


@dataclass(slots=True)
class _Module:
    path: str  # posix relatif, avec extension
    stem: str  # posix relatif, sans extension
    qualname: str
    root: TSNode
    line_count: int
    bindings: dict[str, str] = field(default_factory=dict)  # alias → symbole qualifié


class JavaScriptAnalyzer:
    """Implémente le contrat LanguageAnalyzer pour JavaScript et TypeScript."""

    language: ClassVar[str] = "javascript"
    extensions: ClassVar[frozenset[str]] = frozenset(
        {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
    )
    manifests: ClassVar[frozenset[str]] = frozenset({"package.json"})

    def analyze(
        self,
        files: Sequence[SourceFile],
        subproject: SubProject,
        options: AnalyzerOptions,
    ) -> IRFragment:
        from tree_sitter import Parser

        fragment = IRFragment()
        modules: list[_Module] = []
        for source in files:
            parser = Parser(_language_for(source.path))
            tree = parser.parse(source.text.encode("utf-8"))
            if tree.root_node.has_error:
                fragment.skipped.append(
                    SkippedFile(path=source.path, reason="erreurs de syntaxe (arbre partiel)")
                )
                continue
            stem = source.path.rsplit(".", 1)[0]
            modules.append(
                _Module(
                    path=source.path,
                    stem=stem,
                    qualname=stem.replace("/", "."),
                    root=tree.root_node,
                    line_count=len(source.text.splitlines()),
                )
            )

        by_stem = {m.stem: m for m in modules}
        class_registry: dict[str, NodeKind] = {}
        class_methods: dict[str, set[str]] = {}
        function_registry: set[str] = set()
        for module in modules:
            for node in self._declarations(module.root):
                if node.type in _CLASS_TYPES | {"interface_declaration", "enum_declaration"}:
                    name_node = node.child_by_field_name("name")
                    if name_node is not None:
                        qualname = f"{module.qualname}.{text(name_node)}"
                        kind = (
                            NodeKind.INTERFACE
                            if node.type == "interface_declaration"
                            else NodeKind.ENUM
                            if node.type == "enum_declaration"
                            else NodeKind.CLASS
                        )
                        class_registry[qualname] = kind
                        body = node.child_by_field_name("body")
                        methods = {
                            text(name)
                            for member in (body.named_children if body is not None else [])
                            if member.type == "method_definition"
                            and (name := member.child_by_field_name("name")) is not None
                        }
                        class_methods[qualname] = methods
                elif node.type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node is not None:
                        function_registry.add(f"{module.qualname}.{text(name_node)}")
                elif node.type == "lexical_declaration":
                    for declarator in node.named_children:
                        if declarator.type != "variable_declarator":
                            continue
                        value = declarator.child_by_field_name("value")
                        name_node = declarator.child_by_field_name("name")
                        if (
                            value is not None
                            and name_node is not None
                            and value.type in ("arrow_function", "function_expression", "function")
                        ):
                            function_registry.add(f"{module.qualname}.{text(name_node)}")

        for module in modules:
            module.bindings = self._import_bindings(module, by_stem)

        for module in sorted(modules, key=lambda m: m.qualname):
            _JsModuleExtractor(
                module, subproject.id, class_registry, class_methods, function_registry, fragment
            ).extract()

        fragment.nodes.sort(key=lambda n: n.id)
        fragment.edges.sort(key=lambda e: e.key())
        fragment.skipped.sort(key=lambda s: s.path)
        return fragment

    @staticmethod
    def _declarations(root: TSNode) -> Iterator[TSNode]:
        """Déclarations top-level, débarrassées des enveloppes `export`."""
        for child in root.named_children:
            if child.type == "export_statement":
                declaration = child.child_by_field_name("declaration")
                if declaration is not None:
                    yield declaration
            else:
                yield child

    @staticmethod
    def _import_bindings(module: _Module, by_stem: dict[str, _Module]) -> dict[str, str]:
        bindings: dict[str, str] = {}
        for statement in module.root.named_children:
            if statement.type != "import_statement":
                continue
            source_node = statement.child_by_field_name("source")
            if source_node is None:
                continue
            spec = text(source_node).strip("'\"")
            if not spec.startswith("."):
                continue  # dépendance externe
            base = posixpath.dirname(module.path)
            target_stem = posixpath.normpath(posixpath.join(base, spec))
            target = by_stem.get(target_stem)
            if target is None:
                continue
            for name_node in descendants(statement, frozenset({"import_specifier"})):
                imported = name_node.child_by_field_name("name")
                alias = name_node.child_by_field_name("alias") or imported
                if imported is not None and alias is not None:
                    bindings[text(alias)] = f"{target.qualname}.{text(imported)}"
            bindings.setdefault(f"__module__:{target_stem}", target.qualname)
        return bindings


class _JsModuleExtractor:
    def __init__(
        self,
        module: _Module,
        subproject_id: str,
        class_registry: dict[str, NodeKind],
        class_methods: dict[str, set[str]],
        function_registry: set[str],
        fragment: IRFragment,
    ) -> None:
        self.module = module
        self.sub = subproject_id
        self.class_registry = class_registry
        self.class_methods = class_methods
        self.function_registry = function_registry
        self.fragment = fragment
        self.module_id = f"{subproject_id}/{module.qualname}"

    def _node_id(self, qualname: str) -> str:
        return f"{self.sub}/{qualname}"

    def _location(self, node: TSNode) -> Location:
        return Location(file=self.module.path, line=line_of(node))

    def _resolve_class(self, name: str) -> str | None:
        local = f"{self.module.qualname}.{name}"
        if local in self.class_registry:
            return local
        bound = self.module.bindings.get(name)
        if bound in self.class_registry:
            return bound
        return None

    def extract(self) -> None:
        module = self.module
        modifiers = {
            f"route:{verb} {path}" for verb, path in self._route_registrations()
        }
        modifiers |= {f"ext-import:{package}" for package in self._external_imports()}
        self.fragment.nodes.append(
            Node(
                id=self.module_id,
                kind=NodeKind.MODULE,
                name=module.qualname.rsplit(".", 1)[-1],
                subproject=self.sub,
                location=Location(file=module.path, line=1),
                doc=self._module_doc(),
                modifiers=frozenset(modifiers),
                loc=module.line_count,
            )
        )
        self._import_edges()
        for statement in JavaScriptAnalyzer._declarations(module.root):
            if statement.type in _CLASS_TYPES:
                self._extract_class(statement, NodeKind.CLASS)
            elif statement.type == "interface_declaration":
                self._extract_class(statement, NodeKind.INTERFACE)
            elif statement.type == "enum_declaration":
                self._extract_class(statement, NodeKind.ENUM)
            elif statement.type == "function_declaration":
                self._extract_function(statement, parent=module.qualname, is_method=False)
            elif statement.type == "lexical_declaration":
                self._extract_arrow_functions(statement)

    def _module_doc(self) -> DocInfo | None:
        first = self.module.root.named_children[0] if self.module.root.named_children else None
        if first is not None and first.type == "comment" and text(first).startswith("/**"):
            lines = [
                line.strip().lstrip("*").strip()
                for line in text(first).removeprefix("/**").removesuffix("*/").splitlines()
                if line.strip().lstrip("*").strip()
            ]
            if lines:
                return DocInfo(raw="\n".join(lines), summary=lines[0], format=DocFormat.JSDOC)
        return None

    def _import_edges(self) -> None:
        seen: set[str] = set()
        for key, value in self.module.bindings.items():
            target_qual = value if key.startswith("__module__:") else value.rsplit(".", 1)[0]
            if target_qual != self.module.qualname and target_qual not in seen:
                seen.add(target_qual)
                self.fragment.edges.append(
                    Edge(
                        source=self.module_id,
                        target=self._node_id(target_qual),
                        kind=EdgeKind.IMPORTS,
                        location=Location(file=self.module.path, line=1),
                    )
                )

    def _external_imports(self) -> list[str]:
        """Packages non relatifs importés (T085 : graphe inter-services du monorepo)."""
        packages: set[str] = set()
        for statement in self.module.root.named_children:
            if statement.type == "export_statement":
                statement = statement.child_by_field_name("declaration") or statement
            if statement.type != "import_statement":
                continue
            source_node = statement.child_by_field_name("source")
            if source_node is None:
                continue
            spec = text(source_node).strip("'\"")
            if spec.startswith("."):
                continue
            parts = spec.split("/")
            packages.add("/".join(parts[:2]) if spec.startswith("@") else parts[0])
        return sorted(packages)

    def _route_registrations(self) -> list[tuple[str, str]]:
        routes: list[tuple[str, str]] = []
        for call in descendants(self.module.root, frozenset({"call_expression"})):
            function = call.child_by_field_name("function")
            if function is None or function.type != "member_expression":
                continue
            obj = function.child_by_field_name("object")
            prop = function.child_by_field_name("property")
            if obj is None or prop is None:
                continue
            if text(obj) not in _ROUTE_OBJECTS or text(prop) not in _ROUTE_VERBS:
                continue
            arguments = call.child_by_field_name("arguments")
            if arguments is None or not arguments.named_children:
                continue
            first = arguments.named_children[0]
            if first.type == "string":
                routes.append((text(prop).upper(), text(first).strip("'\"")))
        return sorted(set(routes))

    def _body_calls(self, body: TSNode) -> list[TSNode]:
        """Nœuds d'appel du corps, sans descendre dans les déclarations imbriquées."""
        collected: list[TSNode] = []
        stack: list[TSNode] = [body]
        while stack:
            node = stack.pop()
            for child in node.named_children:
                if child.type in _CLASS_TYPES | {"function_declaration"}:
                    continue
                if child.type in ("call_expression", "new_expression"):
                    collected.append(child)
                stack.append(child)
        return collected

    def _extract_calls(self, body: TSNode, owner_id: str, current_class: str | None) -> None:
        """Arêtes `calls` résolues (T083, FR-009) : constructeurs, this.x(), fonctions."""
        targets: set[tuple[str, int]] = set()
        for call in self._body_calls(body):
            if call.type == "new_expression":
                ctor = call.child_by_field_name("constructor")
                if ctor is not None and ctor.type == "identifier":
                    resolved = self._resolve_class(text(ctor))
                    if resolved is not None and "constructor" in self.class_methods.get(
                        resolved, set()
                    ):
                        targets.add((f"{resolved}.constructor", line_of(call)))
                continue
            function = call.child_by_field_name("function")
            if function is None:
                continue
            if function.type == "identifier":
                name = text(function)
                local = f"{self.module.qualname}.{name}"
                bound = self.module.bindings.get(name)
                if local in self.function_registry:
                    targets.add((local, line_of(call)))
                elif bound is not None and bound in self.function_registry:
                    targets.add((bound, line_of(call)))
            elif function.type == "member_expression" and current_class is not None:
                obj = function.child_by_field_name("object")
                prop = function.child_by_field_name("property")
                if (
                    obj is not None
                    and prop is not None
                    and obj.type == "this"
                    and text(prop) in self.class_methods.get(current_class, set())
                ):
                    targets.add((f"{current_class}.{text(prop)}", line_of(call)))
        for target_qual, line in sorted(targets):
            self.fragment.edges.append(
                Edge(
                    source=owner_id,
                    target=self._node_id(target_qual),
                    kind=EdgeKind.CALLS,
                    location=Location(file=self.module.path, line=line),
                )
            )

    def _extract_class(self, node: TSNode, kind: NodeKind) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = text(name_node)
        qualname = f"{self.module.qualname}.{name}"
        class_id = self._node_id(qualname)
        self.fragment.nodes.append(
            Node(
                id=class_id,
                kind=kind,
                name=name,
                subproject=self.sub,
                location=self._location(node),
                visibility=Visibility.PRIVATE if name.startswith("_") else Visibility.PUBLIC,
                doc=doc_comment(_doc_anchor(node), DocFormat.JSDOC),
                loc=loc_of(node),
            )
        )

        for clause in descendants(
            node, frozenset({"extends_clause", "implements_clause", "class_heritage"})
        ):
            if clause.type == "class_heritage" and any(
                c.type in ("extends_clause", "implements_clause") for c in clause.named_children
            ):
                continue  # les clauses TS internes seront visitées séparément
            edge_kind = (
                EdgeKind.IMPLEMENTS if clause.type == "implements_clause" else EdgeKind.INHERITS
            )
            for identifier in descendants(
                clause, frozenset({"identifier", "type_identifier"})
            ):
                resolved = self._resolve_class(text(identifier))
                if resolved is not None:
                    self.fragment.edges.append(
                        Edge(
                            source=class_id,
                            target=self._node_id(resolved),
                            kind=edge_kind,
                            location=self._location(clause),
                        )
                    )

        body = node.child_by_field_name("body")
        if body is None or kind is not NodeKind.CLASS:
            return
        for member in body.named_children:
            if member.type == "method_definition":
                self._extract_function(member, parent=qualname, is_method=True)
            elif member.type in ("public_field_definition", "field_definition"):
                self._extract_field(member, qualname)

    def _extract_field(self, member: TSNode, class_qual: str) -> None:
        name_node = member.child_by_field_name("name")
        if name_node is None:
            return
        name = text(name_node)
        type_node = member.child_by_field_name("type")
        signature = text(type_node).removeprefix(":").strip() if type_node is not None else ""
        self.fragment.nodes.append(
            Node(
                id=self._node_id(f"{class_qual}.{name}"),
                kind=NodeKind.ATTRIBUTE,
                name=name,
                subproject=self.sub,
                location=self._location(member),
                visibility=self._member_visibility(member, name),
                signature=signature,
            )
        )

    @staticmethod
    def _member_visibility(member: TSNode, name: str) -> Visibility:
        for child in member.children:
            if child.type == "accessibility_modifier" and text(child) in ("private", "protected"):
                return Visibility.PRIVATE
        if name.startswith(("_", "#")):
            return Visibility.PRIVATE
        return Visibility.PUBLIC

    def _extract_function(self, node: TSNode, parent: str, is_method: bool) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = text(name_node)
        parameters = node.child_by_field_name("parameters")
        return_type = node.child_by_field_name("return_type")
        signature = text(parameters) if parameters is not None else "()"
        if return_type is not None:
            signature += f" -> {text(return_type).removeprefix(':').strip()}"
        modifiers = {
            "async" for child in node.children if child.type == "async" or text(child) == "async"
        }
        if any(text(c) == "static" for c in node.children if not c.is_named):
            modifiers.add("static")
        body = node.child_by_field_name("body")
        self.fragment.nodes.append(
            Node(
                id=self._node_id(f"{parent}.{name}"),
                kind=NodeKind.METHOD if is_method else NodeKind.FUNCTION,
                name=name,
                subproject=self.sub,
                location=self._location(node),
                visibility=self._member_visibility(node, name),
                signature=signature,
                doc=doc_comment(_doc_anchor(node), DocFormat.JSDOC),
                modifiers=frozenset(modifiers),
                complexity=count_complexity(body, _DECISIONS) if body is not None else 1,
                loc=loc_of(node),
            )
        )
        if body is not None:
            self._extract_calls(
                body, self._node_id(f"{parent}.{name}"), parent if is_method else None
            )

    def _extract_arrow_functions(self, statement: TSNode) -> None:
        for declarator in statement.named_children:
            if declarator.type != "variable_declarator":
                continue
            value = declarator.child_by_field_name("value")
            name_node = declarator.child_by_field_name("name")
            if value is None or name_node is None:
                continue
            if value.type not in ("arrow_function", "function_expression", "function"):
                continue
            name = text(name_node)
            parameters = value.child_by_field_name("parameters")
            body = value.child_by_field_name("body")
            self.fragment.nodes.append(
                Node(
                    id=self._node_id(f"{self.module.qualname}.{name}"),
                    kind=NodeKind.FUNCTION,
                    name=name,
                    subproject=self.sub,
                    location=self._location(statement),
                    visibility=(
                        Visibility.PRIVATE if name.startswith("_") else Visibility.PUBLIC
                    ),
                    signature=text(parameters) if parameters is not None else "()",
                    doc=doc_comment(_doc_anchor(statement), DocFormat.JSDOC),
                    complexity=count_complexity(body, _DECISIONS) if body is not None else 1,
                    loc=loc_of(statement),
                )
            )
