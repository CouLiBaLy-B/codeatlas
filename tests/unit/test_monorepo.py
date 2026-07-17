"""T069 — Détection des sous-projets d'un monorepo par manifestes (R8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas.config import DEFAULT_EXCLUDES
from codeatlas.monorepo.detect import detect_subprojects

CORPUS = Path(__file__).parents[2] / "examples" / "monorepo-demo"


@pytest.fixture(scope="module")
def subprojects():
    return {s.id: s for s in detect_subprojects(CORPUS, DEFAULT_EXCLUDES)}


class TestDetection:
    def test_all_subprojects_found(self, subprojects) -> None:
        assert set(subprojects) == {"frontend", "shared-lib", "backend", "billing", "legacy-go"}

    def test_languages_from_manifests(self, subprojects) -> None:
        assert subprojects["frontend"].language == "javascript"
        assert subprojects["shared-lib"].language == "javascript"
        assert subprojects["backend"].language == "python"
        assert subprojects["billing"].language == "java"
        assert subprojects["legacy-go"].language == "go"  # non supporté, mais détecté

    def test_manifest_paths_recorded(self, subprojects) -> None:
        assert subprojects["frontend"].manifest == "frontend/package.json"
        assert subprojects["billing"].manifest == "billing/pom.xml"


class TestDeclaredDeps:
    def test_cross_subproject_dependency_resolved(self, subprojects) -> None:
        assert subprojects["frontend"].declared_deps == ("shared-lib",)

    def test_external_dependencies_ignored(self, subprojects) -> None:
        # react et fastapi ne correspondent à aucun sous-projet
        assert "react" not in subprojects["frontend"].declared_deps
        assert subprojects["backend"].declared_deps == ()


class TestRootManifest:
    def test_root_manifest_yields_root_subproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "racine"\n', encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "package.json").write_text('{"name": "sub"}', encoding="utf-8")
        found = {s.id: s for s in detect_subprojects(tmp_path, DEFAULT_EXCLUDES)}
        assert found["main"].root == "."
        assert found["main"].language == "python"
        assert found["sub"].root == "sub"

    def test_no_manifest_yields_no_subproject(self, tmp_path: Path) -> None:
        assert detect_subprojects(tmp_path, DEFAULT_EXCLUDES) == []


def test_determinism() -> None:
    assert detect_subprojects(CORPUS, DEFAULT_EXCLUDES) == detect_subprojects(
        CORPUS, DEFAULT_EXCLUDES
    )
