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

        for module in sorted(modules, key=lambda m: m.qualname):
            _JavaModuleExtractor(
                module, subproject.id, module_names, class_registry, fragment
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
        fragment: IRFragment,
    ) -> None:
        self.module = module
        self.sub = subproject_id
        self.module_names = module_names
        self.class_registry = class_registry
        self.fragment = fragment
        self.module_id = f"{subproject_id}/{module.qualname}"

    def _node_id(self, qualname: str) -> str:
        return f"{self.sub}/{qualname}"

    def _location(self, node: TSNode) -> Location:
        return Location(file=self.module.path, line=line_of(node))

    def _resolve_type(self, name: str) -> tuple[str, NodeKind] | None:
        """Résout un nom de type : import explicite puis même package."""
        for imported in self.module.imports:
            if imported.rsplit(".", 1)[-1] == name and imported in self.module_names:
                package = imported.rsplit(".", 1)[0] if "." in imported else ""
                resolved = self.class_registry.get((package, name))
                if resolved is not None:
                    return resolved
        return self.class_registry.get((self.module.package, name))

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
