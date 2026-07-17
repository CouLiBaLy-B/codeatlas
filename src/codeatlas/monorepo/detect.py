"""Détection des sous-projets d'un monorepo par manifestes standards (R8, FR-015)."""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

from codeatlas.analyzers.base import _is_excluded
from codeatlas.ir.model import SubProject

# ordre = priorité quand plusieurs manifestes coexistent dans un même répertoire
MANIFEST_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("package.json", "javascript"),
    ("pom.xml", "java"),
    ("build.gradle", "java"),
    ("build.gradle.kts", "java"),
    ("go.mod", "go"),  # détecté mais non supporté : listé « non analysé »
)

_DEP_NAME = re.compile(r"^[A-Za-z0-9_.-]+")


def _project_name(manifest: Path, language: str) -> str:
    try:
        if manifest.name == "package.json":
            return str(json.loads(manifest.read_text(encoding="utf-8")).get("name", ""))
        if manifest.name == "pyproject.toml":
            with manifest.open("rb") as handle:
                return str(tomllib.load(handle).get("project", {}).get("name", ""))
        if manifest.name == "pom.xml":
            content = manifest.read_text(encoding="utf-8")
            match = re.search(r"<artifactId>([^<]+)</artifactId>", content)
            return match.group(1).strip() if match else ""
        if manifest.name == "go.mod":
            first = manifest.read_text(encoding="utf-8").splitlines()[0]
            return first.removeprefix("module").strip()
    except (OSError, ValueError, IndexError):  # manifeste illisible → nom vide
        return ""
    return ""


def _declared_names(manifest: Path) -> list[str]:
    try:
        if manifest.name == "package.json":
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return sorted({*data.get("dependencies", {}), *data.get("devDependencies", {})})
        if manifest.name == "pyproject.toml":
            with manifest.open("rb") as handle:
                deps = tomllib.load(handle).get("project", {}).get("dependencies", [])
            names = []
            for entry in deps:
                match = _DEP_NAME.match(entry.strip())
                if match:
                    names.append(match.group(0))
            return sorted(set(names))
    except (OSError, ValueError):
        return []
    return []


_EXTENSION_LANGUAGES: tuple[tuple[str, str], ...] = (
    (".py", "python"),
    (".ts", "javascript"),
    (".tsx", "javascript"),
    (".js", "javascript"),
    (".jsx", "javascript"),
    (".java", "java"),
)


def _infer_language(directory: Path) -> str:
    """Langage dominant d'un répertoire sans manifeste (racine forcée)."""
    counts: dict[str, int] = {}
    for extension, language in _EXTENSION_LANGUAGES:
        counts[language] = counts.get(language, 0) + sum(
            1 for _ in directory.rglob(f"*{extension}")
        )
    best = max(sorted(counts), key=lambda lang: counts[lang])
    return best if counts[best] > 0 else "unknown"


def detect_subprojects(
    root: Path, excludes: Iterable[str], roots: tuple[str, ...] = ()
) -> list[SubProject]:
    """Sous-projets détectés par manifestes, triés par id — déterministe.

    Un répertoire = au plus un sous-projet (priorité selon MANIFEST_LANGUAGES).
    Les dépendances déclarées pointant vers d'autres sous-projets deviennent
    `declared_deps` (source des arêtes `service_dep`). `roots` non vide force
    les racines et court-circuite la découverte ([monorepo].roots — T086).
    """
    patterns = list(excludes)
    found: dict[str, tuple[str, Path]] = {}  # rel_dir → (language, manifest)
    if roots:
        for rel_dir in sorted(set(roots)):
            directory = root / rel_dir
            if not directory.is_dir():
                continue
            for manifest_name, language in MANIFEST_LANGUAGES:
                manifest = directory / manifest_name
                if manifest.is_file():
                    found[rel_dir] = (language, manifest)
                    break
            else:
                found[rel_dir] = (_infer_language(directory), directory / "__aucun__")
    else:
        for manifest_name, language in MANIFEST_LANGUAGES:
            for manifest in sorted(root.rglob(manifest_name)):
                rel = manifest.relative_to(root).as_posix()
                if _is_excluded(rel, patterns):
                    continue
                rel_dir = manifest.parent.relative_to(root).as_posix()
                found.setdefault(rel_dir, (language, manifest))

    names: dict[str, str] = {}  # nom déclaré → id de sous-projet
    subprojects: dict[str, tuple[str, Path, str, str]] = {}
    for rel_dir, (language, manifest) in found.items():
        sub_id = "main" if rel_dir == "." else rel_dir.replace("/", "-")
        name = _project_name(manifest, language)
        subprojects[sub_id] = (language, manifest, rel_dir, name)
        if name:
            names[name] = sub_id

    results = []
    for sub_id, (language, manifest, rel_dir, name) in subprojects.items():
        declared = tuple(
            sorted(
                names[dep]
                for dep in _declared_names(manifest)
                if dep in names and names[dep] != sub_id
            )
        )
        manifest_rel = (
            "" if manifest.name == "__aucun__" else manifest.relative_to(root).as_posix()
        )
        results.append(
            SubProject(
                id=sub_id,
                language=language,
                root=rel_dir,
                manifest=manifest_rel,
                name=name,
                declared_deps=declared,
            )
        )
    return sorted(results, key=lambda s: s.id)
