"""Analyseur Java : tree-sitter → fragment d'IR (R1).

Extraction v1 : modules (un fichier = un module, nommé d'après le package déclaré),
classes/interfaces/enums, champs/méthodes/constructeurs, extends/implements,
imports explicites, Javadoc, complexité, visibilité, annotations (modifiers).
Les graphes d'appels Java sont hors périmètre v1 (documenté dans le plan).
"""

from __future__ import annotations

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
    from tree_sitter import Node as TSNode

_DECISIONS = frozenset(
    {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "ternary_expression",
        "switch_block_statement_group",
    }
)
_TYPE_DECLARATIONS = frozenset(
    {"class_declaration", "interface_declaration", "enum_declaration"}
)
_KIND_BY_TYPE = {
    "class_declaration": NodeKind.CLASS,
    "interface_declaration": NodeKind.INTERFACE,
    "enum_declaration": NodeKind.ENUM,
}


@dataclass(slots=True)
class _Module:
    path: str
    package: str
    qualname: str  # package + nom de fichier
    root: TSNode
    line_count: int
    imports: list[str] = field(default_factory=list)  # symboles qualifiés importés


def _declared_package(root: TSNode) -> str:
    for child in root.named_children:
        if child.type == "package_declaration":
            for part in child.named_children:
                if part.type in ("scoped_identifier", "identifier"):
                    return text(part)
    return ""


def _resolve_type_name(
    name: str,
    module: _Module,
    module_names: set[str],
    class_registry: dict[tuple[str, str], tuple[str, NodeKind]],
) -> tuple[str, NodeKind] | None:
    """Résout un nom de type : import explicite puis même package."""
    for imported in module.imports:
        if imported.rsplit(".", 1)[-1] == name and imported in module_names:
            package = imported.rsplit(".", 1)[0] if "." in imported else ""
            resolved = class_registry.get((package, name))
            if resolved is not None:
                return resolved
    return class_registry.get((module.package, name))


def _first_type_name(node: TSNode) -> str | None:
    for identifier in descendants(node, frozenset({"type_identifier"})):
        return text(identifier)
    return None


@dataclass(slots=True)
class _JavaInventory:
    """Méthodes, types de champs et parent de chaque classe — construit une fois."""

    methods: dict[str, set[str]] = field(default_factory=dict)
    field_types: dict[str, dict[str, str]] = field(default_factory=dict)
    parent: dict[str, str] = field(default_factory=dict)


class JavaAnalyzer:
    """Implémente le contrat LanguageAnalyzer pour Java."""

    language: ClassVar[str] = "java"
    extensions: ClassVar[frozenset[str]] = frozenset({".java"})
    manifests: ClassVar[frozenset[str]] = frozenset(
        {"pom.xml", "build.gradle", "build.gradle.kts"}
    )

    def analyze(
        self,
        files: Sequence[SourceFile],
        subproject: SubProject,
        options: AnalyzerOptions,
    ) -> IRFragment:
        import tree_sitter_java
        from tree_sitter import Language, Parser

        parser = Parser(Language(tree_sitter_java.language()))
        fragment = IRFragment()
        modules: list[_Module] = []
        for source in files:
            tree = parser.parse(source.text.encode("utf-8"))
            if tree.root_node.has_error:
                fragment.skipped.append(
                    SkippedFile(path=source.path, reason="erreurs de syntaxe (arbre partiel)")
                )
                continue
            stem = source.path.rsplit("/", 1)[-1].removesuffix(".java")
            package = _declared_package(tree.root_node)
            qualname = f"{package}.{stem}" if package else stem
            module = _Module(
                path=source.path,
                package=package,
                qualname=qualname,
                root=tree.root_node,
                line_count=len(source.text.splitlines()),
            )
            for child in tree.root_node.named_children:
                if child.type == "import_declaration":
                    for part in child.named_children:
                        if part.type == "scoped_identifier":
                            module.imports.append(text(part))
            modules.append(module)

        # registre global : (package, NomDeClasse) → qualname du type dans l'IR
        module_names = {m.qualname for m in modules}
        class_registry: dict[tuple[str, str], tuple[str, NodeKind]] = {}
        for module in modules:
            for declaration in module.root.named_children:
                if declaration.type in _TYPE_DECLARATIONS:
                    name_node = declaration.child_by_field_name("name")
                    if name_node is not None:
                        name = text(name_node)
                        class_registry[(module.package, name)] = (
                            f"{module.qualname}.{name}",
                            _KIND_BY_TYPE[declaration.type],
                        )

        # inventaire : méthodes, types de champs, parent — pour la résolution d'appels
        inventory = _JavaInventory()
        for module in modules:
            for declaration in module.root.named_children:
                if declaration.type not in _TYPE_DECLARATIONS:
                    continue
                name_node = declaration.child_by_field_name("name")
                body = declaration.child_by_field_name("body")
                if name_node is None or body is None:
                    continue
                qualname = f"{module.qualname}.{text(name_node)}"
                methods: set[str] = set()
                fields: dict[str, str] = {}
                for member in body.named_children:
                    if member.type in ("method_declaration", "constructor_declaration"):
                        member_name = member.child_by_field_name("name")
                        if member_name is not None:
                            methods.add(text(member_name))
                    elif member.type == "field_declaration":
                        type_node = member.child_by_field_name("type")
                        type_name = _first_type_name(type_node) if type_node else None
                        resolved = (
                            _resolve_type_name(type_name, module, module_names, class_registry)
                            if type_name
                            else None
                        )
                        if resolved is None:
                            continue
                        for declarator in member.named_children:
                            if declarator.type == "variable_declarator":
                                field_name = declarator.child_by_field_name("name")
                                if field_name is not None:
                                    fields[text(field_name)] = resolved[0]
                inventory.methods[qualname] = methods
                inventory.field_types[qualname] = fields
                superclass = declaration.child_by_field_name("superclass")
                parent_name = _first_type_name(superclass) if superclass else None
                if parent_name:
                    resolved = _resolve_type_name(
                        parent_name, module, module_names, class_registry
                    )
                    if resolved is not None:
                        inventory.parent[qualname] = resolved[0]

        for module in sorted(modules, key=lambda m: m.qualname):
            _JavaModuleExtractor(
                module, subproject.id, module_names, class_registry, inventory, fragment
            ).extract()

        fragment.nodes.sort(key=lambda n: n.id)
        fragment.edges.sort(key=lambda e: e.key())
        fragment.skipped.sort(key=lambda s: s.path)
        return fragment


class _JavaModuleExtractor:
    def __init__(
        self,
        module: _Module,
        subproject_id: str,
        module_names: set[str],
        class_registry: dict[tuple[str, str], tuple[str, NodeKind]],
        inventory: _JavaInventory,
        fragment: IRFragment,
    ) -> None:
        self.module = module
        self.sub = subproject_id
        self.module_names = module_names
        self.class_registry = class_registry
        self.inventory = inventory
        self.fragment = fragment
        self.module_id = f"{subproject_id}/{module.qualname}"

    def _node_id(self, qualname: str) -> str:
        return f"{self.sub}/{qualname}"

    def _location(self, node: TSNode) -> Location:
        return Location(file=self.module.path, line=line_of(node))

    def _resolve_type(self, name: str) -> tuple[str, NodeKind] | None:
        return _resolve_type_name(name, self.module, self.module_names, self.class_registry)

    def _method_owner(self, start_class: str, method: str) -> str | None:
        """Classe (dans la chaîne d'héritage) qui définit `method`, sinon None."""
        current: str | None = start_class
        for _ in range(8):  # garde-fou contre un cycle d'héritage
            if current is None:
                return None
            if method in self.inventory.methods.get(current, set()):
                return current
            current = self.inventory.parent.get(current)
        return None

    def extract(self) -> None:
        module = self.module
        self.fragment.nodes.append(
            Node(
                id=self.module_id,
                kind=NodeKind.MODULE,
                name=module.qualname.rsplit(".", 1)[-1],
                subproject=self.sub,
                location=Location(file=module.path, line=1),
                loc=module.line_count,
            )
        )
        for imported in sorted(set(module.imports)):
            if imported in self.module_names and imported != module.qualname:
                self.fragment.edges.append(
                    Edge(
                        source=self.module_id,
                        target=self._node_id(imported),
                        kind=EdgeKind.IMPORTS,
                        location=Location(file=module.path, line=1),
                    )
                )
        for declaration in module.root.named_children:
            if declaration.type in _TYPE_DECLARATIONS:
                self._extract_type(declaration)

    def _modifiers_and_visibility(self, node: TSNode) -> tuple[set[str], Visibility]:
        modifiers: set[str] = set()
        visibility = Visibility.PUBLIC
        for child in node.children:
            if child.type != "modifiers":
                continue
            for modifier in child.children:
                token = text(modifier)
                if modifier.type in ("marker_annotation", "annotation"):
                    modifiers.add(f"decorator:{token.lstrip('@')}")
                elif token in ("private", "protected"):
                    visibility = Visibility.PRIVATE
                elif token in ("static", "abstract", "final"):
                    modifiers.add(token)
        return modifiers, visibility

    def _extract_type(self, declaration: TSNode) -> None:
        name_node = declaration.child_by_field_name("name")
        if name_node is None:
            return
        name = text(name_node)
        qualname = f"{self.module.qualname}.{name}"
        type_id = self._node_id(qualname)
        modifiers, visibility = self._modifiers_and_visibility(declaration)
        self.fragment.nodes.append(
            Node(
                id=type_id,
                kind=_KIND_BY_TYPE[declaration.type],
                name=name,
                subproject=self.sub,
                location=self._location(declaration),
                visibility=visibility,
                doc=doc_comment(declaration, DocFormat.JAVADOC),
                modifiers=frozenset(modifiers),
                loc=loc_of(declaration),
            )
        )

        superclass = declaration.child_by_field_name("superclass")
        if superclass is not None:
            for identifier in descendants(superclass, frozenset({"type_identifier"})):
                self._type_edge(type_id, text(identifier), EdgeKind.INHERITS, superclass)
        interfaces = declaration.child_by_field_name("interfaces")
        if interfaces is not None:
            for identifier in descendants(interfaces, frozenset({"type_identifier"})):
                self._type_edge(type_id, text(identifier), EdgeKind.IMPLEMENTS, interfaces)

        body = declaration.child_by_field_name("body")
        if body is None:
            return
        for member in body.named_children:
            if member.type in ("method_declaration", "constructor_declaration"):
                self._extract_method(member, qualname)
            elif member.type == "field_declaration":
                self._extract_field(member, qualname)

    def _type_edge(self, source_id: str, name: str, kind: EdgeKind, node: TSNode) -> None:
        resolved = self._resolve_type(name)
        if resolved is None:
            return
        target_qual, target_kind = resolved
        if kind is EdgeKind.INHERITS and target_kind is NodeKind.INTERFACE:
            kind = EdgeKind.IMPLEMENTS
        self.fragment.edges.append(
            Edge(
                source=source_id,
                target=self._node_id(target_qual),
                kind=kind,
                location=self._location(node),
            )
        )

    def _extract_field(self, member: TSNode, class_qual: str) -> None:
        modifiers, visibility = self._modifiers_and_visibility(member)
        type_node = member.child_by_field_name("type")
        for declarator in member.named_children:
            if declarator.type != "variable_declarator":
                continue
            name_node = declarator.child_by_field_name("name")
            if name_node is None:
                continue
            name = text(name_node)
            self.fragment.nodes.append(
                Node(
                    id=self._node_id(f"{class_qual}.{name}"),
                    kind=NodeKind.ATTRIBUTE,
                    name=name,
                    subproject=self.sub,
                    location=self._location(member),
                    visibility=visibility,
                    signature=text(type_node) if type_node is not None else "",
                    modifiers=frozenset(modifiers),
                )
            )

    def _extract_method(self, member: TSNode, class_qual: str) -> None:
        name_node = member.child_by_field_name("name")
        if name_node is None:
            return
        name = text(name_node)
        modifiers, visibility = self._modifiers_and_visibility(member)
        parameters = member.child_by_field_name("parameters")
        return_type = member.child_by_field_name("type")
        signature = text(parameters) if parameters is not None else "()"
        if return_type is not None:
            signature += f" -> {text(return_type)}"
        body = member.child_by_field_name("body")
        self.fragment.nodes.append(
            Node(
                id=self._node_id(f"{class_qual}.{name}"),
                kind=NodeKind.METHOD,
                name=name,
                subproject=self.sub,
                location=self._location(member),
                visibility=visibility,
                signature=signature,
                doc=doc_comment(member, DocFormat.JAVADOC),
                modifiers=frozenset(modifiers),
                complexity=count_complexity(body, _DECISIONS) if body is not None else 1,
                loc=loc_of(member),
            )
        )
        if body is not None:
            self._extract_calls(member, body, class_qual, f"{class_qual}.{name}")

    def _extract_calls(
        self, member: TSNode, body: TSNode, class_qual: str, owner_qual: str
    ) -> None:
        """Arêtes `calls` résolues par types déclarés (T083, FR-009)."""
        var_types: dict[str, str] = {}
        parameters = member.child_by_field_name("parameters")
        if parameters is not None:
            for parameter in parameters.named_children:
                if parameter.type != "formal_parameter":
                    continue
                type_node = parameter.child_by_field_name("type")
                name_node = parameter.child_by_field_name("name")
                type_name = _first_type_name(type_node) if type_node else None
                resolved = self._resolve_type(type_name) if type_name else None
                if resolved is not None and name_node is not None:
                    var_types[text(name_node)] = resolved[0]
        for declaration in descendants(body, frozenset({"local_variable_declaration"})):
            type_node = declaration.child_by_field_name("type")
            type_name = _first_type_name(type_node) if type_node else None
            resolved = self._resolve_type(type_name) if type_name else None
            if resolved is None:
                continue
            for declarator in declaration.named_children:
                if declarator.type == "variable_declarator":
                    name_node = declarator.child_by_field_name("name")
                    if name_node is not None:
                        var_types[text(name_node)] = resolved[0]

        field_types = self.inventory.field_types.get(class_qual, {})
        targets: set[tuple[str, int]] = set()

        for creation in descendants(body, frozenset({"object_creation_expression"})):
            type_node = creation.child_by_field_name("type")
            type_name = _first_type_name(type_node) if type_node else None
            resolved = self._resolve_type(type_name) if type_name else None
            if resolved is not None and type_name in self.inventory.methods.get(resolved[0], set()):
                targets.add((f"{resolved[0]}.{type_name}", line_of(creation)))

        for invocation in descendants(body, frozenset({"method_invocation"})):
            name_node = invocation.child_by_field_name("name")
            if name_node is None:
                continue
            method = text(name_node)
            obj = invocation.child_by_field_name("object")
            owner_class: str | None = None
            if obj is None or obj.type == "this":
                owner_class = class_qual
            elif obj.type == "super":
                owner_class = self.inventory.parent.get(class_qual)
            elif obj.type == "identifier":
                identifier = text(obj)
                owner_class = var_types.get(identifier) or field_types.get(identifier)
            elif obj.type == "field_access":
                inner = obj.child_by_field_name("object")
                field_node = obj.child_by_field_name("field")
                if inner is not None and inner.type == "this" and field_node is not None:
                    owner_class = field_types.get(text(field_node))
            if owner_class is None:
                continue
            defining = self._method_owner(owner_class, method)
            if defining is not None:
                targets.add((f"{defining}.{method}", line_of(invocation)))

        for target_qual, line in sorted(targets):
            self.fragment.edges.append(
                Edge(
                    source=self._node_id(owner_qual),
                    target=self._node_id(target_qual),
                    kind=EdgeKind.CALLS,
                    location=Location(file=self.module.path, line=line),
                )
            )
