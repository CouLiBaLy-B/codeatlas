"""T081 — Les pages manuelles `[site].extra_nav` ne sont JAMAIS écrasées (contrat cli.md)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main

MANUAL_CONTENT = "# Guide maison\n\nContenu écrit à la main — doit survivre aux régénérations.\n"


@pytest.fixture()
def corpus_copy(tmp_path: Path, corpus: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(corpus, target)
    (target / "codeatlas.toml").write_text(
        '[site]\nextra_nav = ["guides/intro.md"]\n', encoding="utf-8"
    )
    return target


class TestExtraNavPreservation:
    def test_first_build_scaffolds_a_stub(
        self, corpus_copy: Path, tmp_path: Path, runner: CliRunner
    ) -> None:
        out = tmp_path / "out"
        result = runner.invoke(main, ["build", str(corpus_copy), "--out", str(out)])
        assert result.exit_code == 0, result.output
        stub = out / "docs" / "guides" / "intro.md"
        assert stub.is_file()

    def test_manual_edits_survive_rebuild(
        self, corpus_copy: Path, tmp_path: Path, runner: CliRunner
    ) -> None:
        out = tmp_path / "out"
        assert runner.invoke(main, ["build", str(corpus_copy), "--out", str(out)]).exit_code == 0
        page = out / "docs" / "guides" / "intro.md"
        page.write_text(MANUAL_CONTENT, encoding="utf-8")

        assert runner.invoke(main, ["build", str(corpus_copy), "--out", str(out)]).exit_code == 0
        assert page.read_text(encoding="utf-8") == MANUAL_CONTENT  # jamais écrasée

    def test_manual_page_listed_in_nav(
        self, corpus_copy: Path, tmp_path: Path, runner: CliRunner
    ) -> None:
        out = tmp_path / "out"
        assert runner.invoke(main, ["build", str(corpus_copy), "--out", str(out)]).exit_code == 0
        assert "guides/intro.md" in (out / "mkdocs.yml").read_text(encoding="utf-8")


class TestSvgOptionHonesty:
    """T082 — l'option SVG doit être explicitement signalée non supportée (pas un no-op)."""

    def test_svg_flag_emits_explicit_warning(
        self, corpus: Path, tmp_path: Path, runner: CliRunner
    ) -> None:
        import json

        report_path = tmp_path / "report.json"
        result = runner.invoke(
            main,
            [
                "build",
                str(corpus),
                "--out",
                str(tmp_path / "out"),
                "--svg",
                "--json-report",
                str(report_path),
            ],
        )
        assert result.exit_code == 0, result.output
        report = json.loads(report_path.read_text(encoding="utf-8"))
        codes = {w["code"] for w in report["warnings"]}
        assert "svg-unavailable" in codes
        assert "SVG" in result.output  # signalé aussi sur la console

    def test_no_svg_flag_no_warning(
        self, corpus: Path, tmp_path: Path, runner: CliRunner
    ) -> None:
        import json

        report_path = tmp_path / "report.json"
        args = ["build", str(corpus), "--out", str(tmp_path / "out")]
        result = runner.invoke(main, [*args, "--json-report", str(report_path)])
        assert result.exit_code == 0
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert not any(w["code"] == "svg-unavailable" for w in report["warnings"])
