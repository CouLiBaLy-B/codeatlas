"""Contrat des analyseurs de langage, registre et découverte des fichiers sources.

Contrat : specs/001-intelligent-doc-generator/contracts/analyzer-protocol.md.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import ClassVar, Protocol, runtime_checkable

from codeatlas.ir.model import Edge, Node, SkippedFile, SubProject


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Fichier source lu par le cœur — chemin POSIX relatif à la racine analysée."""

    path: str
    text: str


@dataclass(frozen=True, slots=True)
class AnalyzerOptions:
    include_private: bool = False


@dataclass(slots=True)
class IRFragment:
    """Production d'un analyseur : à fusionner dans le CodeGraph par le cœur."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)


@runtime_checkable
class LanguageAnalyzer(Protocol):
    """Contrat d'un analyseur de langage. Ajouter un langage = une implémentation."""

    language: ClassVar[str]
    extensions: ClassVar[frozenset[str]]
    manifests: ClassVar[frozenset[str]]

    def analyze(
        self,
        files: Sequence[SourceFile],
        subproject: SubProject,
        options: AnalyzerOptions,
    ) -> IRFragment:
        """Produit un fragment d'IR. Ne lève jamais pour un fichier invalide."""
        ...


_REGISTRY: dict[str, LanguageAnalyzer] = {}


class AnalyzerUnavailableError(Exception):
    """Le langage est connu mais son extra n'est pas installé."""


def register(analyzer: LanguageAnalyzer) -> None:
    _REGISTRY[analyzer.language] = analyzer


def available_analyzers() -> dict[str, LanguageAnalyzer]:
    _ensure_builtin_registered()
    return dict(sorted(_REGISTRY.items()))


def _has_module(name: str) -> bool:
    from importlib.util import find_spec

    try:
        return find_spec(name) is not None
    except (ImportError, ValueError):  # pragma: no cover
        return False


def _ensure_builtin_registered() -> None:
    if "python" not in _REGISTRY:
        from codeatlas.analyzers.python.analyzer import PythonAnalyzer

        register(PythonAnalyzer())
    if (
        "javascript" not in _REGISTRY
        and _has_module("tree_sitter")
        and _has_module("tree_sitter_javascript")
        and _has_module("tree_sitter_typescript")
    ):
        from codeatlas.analyzers.javascript.analyzer import JavaScriptAnalyzer

        register(JavaScriptAnalyzer())
    if "java" not in _REGISTRY and _has_module("tree_sitter") and _has_module("tree_sitter_java"):
        from codeatlas.analyzers.java.analyzer import JavaAnalyzer

        register(JavaAnalyzer())


# -- découverte des fichiers -------------------------------------------------


def _is_excluded(posix_path: str, patterns: Iterable[str]) -> bool:
    path = PurePosixPath(posix_path)
    for pattern in patterns:
        if fnmatch.fnmatch(posix_path, pattern):
            return True
        # `**/name/**` doit aussi exclure les chemins DÉBUTANT par `name/`
        # et `.*/` les dossiers cachés à toute profondeur.
        inner = pattern.removeprefix("**/")
        if inner.endswith("/**"):
            directory = inner.removesuffix("/**")
            if any(fnmatch.fnmatch(part, directory) for part in path.parts[:-1]):
                return True
        elif fnmatch.fnmatch(path.name, inner):
            return True
    return False


GENERATED_MARKER = ".codeatlas-generated"


def _generated_dirs(root: Path) -> set[str]:
    """Répertoires (POSIX, relatifs à `root`) portant le marqueur de génération.

    Un site produit par CodeAtlas dépose `.codeatlas-generated` à sa racine : ses
    fichiers (scripts vendorisés, doc rendue) ne doivent jamais être analysés
    (feature 005, US3) — sinon ils créent de faux modules et sous-projets.
    """
    marked: set[str] = set()
    for marker in root.rglob(GENERATED_MARKER):
        parent = marker.parent.relative_to(root).as_posix()
        marked.add("" if parent == "." else parent)
    return marked


def _under_generated(rel_posix: str, generated: set[str]) -> bool:
    """Le chemin est-il dans (ou sous) un répertoire marqué généré ?"""
    return any(
        marked == "" or rel_posix == marked or rel_posix.startswith(f"{marked}/")
        for marked in generated
    )


def discover_files(
    root: Path,
    excludes: Iterable[str],
    extensions: frozenset[str],
    include_generated: bool = False,
) -> tuple[list[SourceFile], list[SkippedFile]]:
    """Liste triée des fichiers sources d'une racine, exclusions appliquées.

    Un fichier illisible (encodage, droits) devient une entrée `skipped` —
    jamais une exception (constitution IV). Les répertoires marqués générés sont
    ignorés sauf `include_generated=True` (réintégration explicite, FR-008).
    """
    sources: list[SourceFile] = []
    skipped: list[SkippedFile] = []
    patterns = list(excludes)
    generated = set() if include_generated else _generated_dirs(root)
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in extensions:
            continue
        rel = path.relative_to(root).as_posix()
        if _is_excluded(rel, patterns):
            continue
        if generated and _under_generated(rel, generated):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append(SkippedFile(path=rel, reason="encodage non UTF-8"))
        except OSError as exc:
            skipped.append(SkippedFile(path=rel, reason=f"lecture impossible : {exc.strerror}"))
        else:
            sources.append(SourceFile(path=rel, text=text))
    return sources, skipped
