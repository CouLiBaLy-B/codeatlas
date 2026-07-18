"""T019 — Changelog architectural : baselines archivées → page ordonnée du site."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main
from tests.integration.test_diff_cli import introduce_cycle

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(CORPUS, target)
    return target


class TestChangelogPage:
    def test_two_archives_produce_ordered_page(
        self, repo: Path, tmp_path: Path, runner: CliRunner
    ) -> None:
        assert runner.invoke(main, ["baseline", str(repo), "--archive", "v1"]).exit_code == 0
        introduce_cycle(repo)
        assert runner.invoke(main, ["baseline", str(repo), "--archive", "v2"]).exit_code == 0

        out = tmp_path / "out"
        result = runner.invoke(main, ["build", str(repo), "--out", str(out), "--no-site"])
        assert result.exit_code == 0, result.output

        page = (out / "docs" / "changelog.md").read_text(encoding="utf-8")
        assert "v1" in page and "v2" in page
        assert page.index("## v2") < page.index("## v1")  # plus récent en premier
        assert "shopdemo.models" in page  # le cycle apparu est détaillé
        assert "changelog.md" in (out / "mkdocs.yml").read_text(encoding="utf-8")

    def test_natural_sort_of_labels(self, repo: Path, tmp_path: Path, runner: CliRunner) -> None:
        for label in ("v2", "v10"):
            assert runner.invoke(
                main, ["baseline", str(repo), "--archive", label]
            ).exit_code == 0
        out = tmp_path / "out"
        assert runner.invoke(
            main, ["build", str(repo), "--out", str(out), "--no-site"]
        ).exit_code == 0
        page = (out / "docs" / "changelog.md").read_text(encoding="utf-8")
        assert page.index("## v10") < page.index("## v2")  # v10 > v2 (tri naturel)

    def test_no_archive_no_page(self, repo: Path, tmp_path: Path, runner: CliRunner) -> None:
        out = tmp_path / "out"
        assert runner.invoke(
            main, ["build", str(repo), "--out", str(out), "--no-site"]
        ).exit_code == 0
        assert not (out / "docs" / "changelog.md").exists()
