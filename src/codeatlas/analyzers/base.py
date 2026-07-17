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


def _ensure_builtin_registered() -> None:
    if "python" not in _REGISTRY:
        from codeatlas.analyzers.python.analyzer import PythonAnalyzer

        register(PythonAnalyzer())


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


def discover_files(
    root: Path,
    excludes: Iterable[str],
    extensions: frozenset[str],
) -> tuple[list[SourceFile], list[SkippedFile]]:
    """Liste triée des fichiers sources d'une racine, exclusions appliquées.

    Un fichier illisible (encodage, droits) devient une entrée `skipped` —
    jamais une exception (constitution IV).
    """
    sources: list[SourceFile] = []
    skipped: list[SkippedFile] = []
    patterns = list(excludes)
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in extensions:
            continue
        rel = path.relative_to(root).as_posix()
        if _is_excluded(rel, patterns):
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
