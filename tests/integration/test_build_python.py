"""T021 — Scénarios d'acceptation US1 de bout en bout via la CLI `build`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main

# SC-003 : tous les symboles publics du corpus doivent figurer dans la référence API.
PUBLIC_CLASSES = [
    "Product",
    "DigitalProduct",
    "OrderLine",
    "Order",
    "InMemoryRepo",
    "CatalogService",
    "OrderService",
]
PUBLIC_FUNCTIONS = ["apply_legacy_discount", "audit_catalog", "main"]


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    corpus = Path(__file__).parents[2] / "examples" / "python-demo"
    out = tmp_path_factory.mktemp("atlas") / "docs-out"
    report_path = out.parent / "report.json"
    result = CliRunner().invoke(
        main,
        ["build", str(corpus), "--out", str(out), "--json-report", str(report_path)],
    )
    assert result.exit_code == 0, result.output
    return out, report_path.read_text(encoding="utf-8")


def _all_docs_text(out: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted((out / "docs").rglob("*.md"))
    )


class TestScenario1SiteComplet:
    def test_site_html_generated_and_navigable(self, built: tuple[Path, str]) -> None:
        out, _ = built
        assert (out / "site" / "index.html").is_file()
        assert (out / "mkdocs.yml").is_file()

    def test_overview_diagrams_and_api_reference_present(self, built: tuple[Path, str]) -> None:
        out, _ = built
        docs = _all_docs_text(out)
        assert "classDiagram" in docs
        assert "flowchart" in docs or "graph LR" in docs
        for symbol in (*PUBLIC_CLASSES, *PUBLIC_FUNCTIONS):
            assert symbol in docs, f"symbole public absent de la référence API : {symbol}"

    def test_standalone_mmd_artifacts_emitted(self, built: tuple[Path, str]) -> None:
        out, _ = built
        mmd_files = list((out / "diagrams").glob("*.mmd"))
        assert mmd_files, "aucun artefact .mmd autonome émis (FR-014)"

    def test_site_is_offline_no_cdn_urls(self, built: tuple[Path, str]) -> None:
        out, _ = built
        index = (out / "site" / "index.html").read_text(encoding="utf-8")
        for marker in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com", "fonts.googleapis"):
            assert marker not in index, f"référence CDN dans le site : {marker}"
        assert (out / "site" / "assets" / "mermaid.min.js").is_file()


class TestScenario2CycleMisEnEvidence:
    def test_cycle_listed_and_highlighted(self, built: tuple[Path, str]) -> None:
        out, _ = built
        docs = _all_docs_text(out)
        assert "shopdemo.legacy" in docs
        assert "shopdemo.services" in docs
        assert "stroke:#d33" in docs  # arêtes du cycle stylées


class TestScenario3ToleranceFichierInvalide:
    def test_invalid_file_reported_but_build_succeeds(self, built: tuple[Path, str]) -> None:
        out, report_text = built
        docs = _all_docs_text(out)
        assert "shopdemo/broken/invalid_syntax.py" in docs
        report = json.loads(report_text)
        assert report["counts"]["files_skipped"] == 1
        assert report["skipped"][0]["path"] == "shopdemo/broken/invalid_syntax.py"
        assert "SyntaxError" in report["skipped"][0]["reason"]


class TestScenario4DoubleRunIdentique:
    def test_json_report_schema(self, built: tuple[Path, str]) -> None:
        _, report_text = built
        report = json.loads(report_text)
        assert report["report_version"] == 1
        # 15 modules analysables dans le corpus (webapp et quality inclus)
        assert report["counts"]["files_analyzed"] == 15
        assert report["counts"]["nodes"] > 30


def test_no_site_flag_emits_artifacts_only(tmp_path: Path, corpus: Path, runner: CliRunner) -> None:
    out = tmp_path / "artefacts"
    result = runner.invoke(main, ["build", str(corpus), "--out", str(out), "--no-site"])
    assert result.exit_code == 0, result.output
    assert (out / "docs").is_dir()
    assert not (out / "site").exists()


def test_empty_repository_fails_with_clear_error(tmp_path: Path, runner: CliRunner) -> None:
    empty = tmp_path / "vide"
    empty.mkdir()
    result = runner.invoke(main, ["build", str(empty)])
    assert result.exit_code == 1
    assert "aucun fichier analysable" in result.output


def test_unknown_config_key_is_usage_error(tmp_path: Path, corpus: Path, runner: CliRunner) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("[projet]\n", encoding="utf-8")
    result = runner.invoke(main, ["build", str(corpus), "--config", str(bad)])
    assert result.exit_code == 2
