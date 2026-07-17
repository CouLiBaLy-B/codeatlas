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


class TestForcedRoots:
    """T086 — `[monorepo].roots` force les racines de sous-projets."""

    def test_forced_roots_override_detection(self) -> None:
        found = {
            s.id
            for s in detect_subprojects(CORPUS, DEFAULT_EXCLUDES, roots=("frontend", "backend"))
        }
        assert found == {"frontend", "backend"}

    def test_forced_root_without_manifest_is_unknown_language(self, tmp_path: Path) -> None:
        (tmp_path / "mystery").mkdir()
        (tmp_path / "mystery" / "code.py").write_text('"""x."""\n', encoding="utf-8")
        detected = detect_subprojects(tmp_path, DEFAULT_EXCLUDES, roots=("mystery",))
        found = {s.id: s for s in detected}
        assert found["mystery"].language == "python"  # inféré des extensions présentes


class TestLanguagesFilterInMonorepo:
    """T087 — `[analysis].languages` s'applique aussi en mode monorepo."""

    def test_only_selected_language_analyzed(self) -> None:
        from dataclasses import replace

        from codeatlas import api
        from codeatlas.config import Config
        from codeatlas.ir.model import NodeKind

        config = replace(Config(), analysis=replace(Config().analysis, languages=("python",)))
        graph = api.analyze(CORPUS, config)
        analyzed_subs = {m.subproject for m in graph.iter_nodes(NodeKind.MODULE)}
        assert analyzed_subs == {"backend"}


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


class TestServiceLinkNature:
    """T085 — service_dep depuis les imports croisés, nature restituée dans le rendu."""

    def _npm_package(self, root: Path, name: str, source: str = "") -> None:
        (root / name).mkdir()
        (root / name / "package.json").write_text(f'{{"name": "{name}"}}', encoding="utf-8")
        default = f"/** Module {name}. */\nexport function {name}(): void {{}}\n"
        (root / name / "index.ts").write_text(source or default, encoding="utf-8")

    def test_undeclared_import_creates_service_dep_labelled_import(
        self, tmp_path: Path
    ) -> None:
        from codeatlas import api
        from codeatlas.ir.model import EdgeKind
        from codeatlas.renderers.mermaid.services import render_services

        consumer_source = (
            "/** Consomme provider SANS le déclarer. */\n"
            "import { provider } from 'provider';\n\n"
            "export function use(): void {\n  provider();\n}\n"
        )
        self._npm_package(tmp_path, "consumer", consumer_source)
        self._npm_package(tmp_path, "provider")
        graph = api.analyze(tmp_path)
        service_deps = {
            (e.source, e.target) for e in graph.edges_of_kind(EdgeKind.SERVICE_DEP)
        }
        assert ("consumer", "provider") in service_deps
        assert "-->|import|" in render_services(graph)

    def test_declared_dependency_labelled_declared(self) -> None:
        from codeatlas import api
        from codeatlas.renderers.mermaid.services import render_services

        rendered = render_services(api.analyze(CORPUS))
        assert "-->|déclaré|" in rendered


def test_determinism() -> None:
    assert detect_subprojects(CORPUS, DEFAULT_EXCLUDES) == detect_subprojects(
        CORPUS, DEFAULT_EXCLUDES
    )
