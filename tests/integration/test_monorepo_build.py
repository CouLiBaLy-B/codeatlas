"""T070 — Scénarios d'acceptation US6 : monorepo polyglotte → site unique."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main

MONOREPO = Path(__file__).parents[2] / "examples" / "monorepo-demo"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("atlas-us6") / "out"
    result = CliRunner().invoke(main, ["build", str(MONOREPO), "--out", str(out)])
    assert result.exit_code == 0, result.output
    return out


class TestScenario1SiteUnique:
    def test_each_supported_subproject_documented(self, built: Path) -> None:
        pages = {p.name for p in (built / "docs" / "modules").glob("*.md")}
        assert "frontend.src.app.md" in pages          # TypeScript
        assert "backend.backend_app.api.md" in pages   # Python
        assert "billing.com.billing.Invoice.md" in pages  # Java

    def test_classes_from_all_languages_present(self, built: Path) -> None:
        docs = "\n".join(
            p.read_text(encoding="utf-8") for p in sorted((built / "docs").rglob("*.md"))
        )
        assert "AppShell" in docs
        assert "OrdersApi" in docs
        assert "Invoice" in docs


class TestScenario2GrapheInterServices:
    def test_monorepo_page_with_services_graph(self, built: Path) -> None:
        page = (built / "docs" / "monorepo.md").read_text(encoding="utf-8")
        assert "frontend" in page
        assert "shared-lib" in page
        assert "graph LR" in page or "flowchart" in page

    def test_declared_dependency_rendered(self, built: Path) -> None:
        page = (built / "docs" / "monorepo.md").read_text(encoding="utf-8")
        # l'arête front → shared-lib vient des dépendances déclarées
        assert "-->" in page

    def test_monorepo_page_in_nav(self, built: Path) -> None:
        assert "monorepo.md" in (built / "mkdocs.yml").read_text(encoding="utf-8")


class TestScenario3LangageNonSupporte:
    def test_unsupported_subproject_listed_not_fatal(self, built: Path) -> None:
        page = (built / "docs" / "monorepo.md").read_text(encoding="utf-8")
        assert "legacy-go" in page
        assert "go" in page
