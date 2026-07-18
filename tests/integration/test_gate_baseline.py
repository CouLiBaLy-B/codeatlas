"""T013 — Gate CI contre baseline : exit 3 sur régression, création au 1er run."""

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


class TestExitCodes:
    def test_violated_rule_exits_3(self, repo: Path, runner: CliRunner) -> None:
        assert runner.invoke(main, ["baseline", str(repo)]).exit_code == 0
        introduce_cycle(repo)
        result = runner.invoke(
            main, ["check", str(repo), "--against-baseline", "--fail-on-new-cycles"]
        )
        assert result.exit_code == 3
        assert "fail-on-new-cycles" in result.output

    def test_no_rule_configured_informative_only(self, repo: Path, runner: CliRunner) -> None:
        assert runner.invoke(main, ["baseline", str(repo)]).exit_code == 0
        introduce_cycle(repo)
        result = runner.invoke(main, ["check", str(repo), "--against-baseline"])
        assert result.exit_code == 0, result.output

    def test_rule_enabled_but_no_regression_passes(self, repo: Path, runner: CliRunner) -> None:
        assert runner.invoke(main, ["baseline", str(repo)]).exit_code == 0
        result = runner.invoke(
            main, ["check", str(repo), "--against-baseline", "--fail-on-new-cycles"]
        )
        assert result.exit_code == 0, result.output


class TestFirstRun:
    def test_missing_baseline_created_and_success(self, repo: Path, runner: CliRunner) -> None:
        result = runner.invoke(
            main, ["check", str(repo), "--against-baseline", "--fail-on-new-cycles"]
        )
        assert result.exit_code == 0, result.output
        assert (repo / ".codeatlas" / "baseline.json").is_file()
        assert "baseline" in result.output.lower()


class TestConfigFile:
    def test_rules_from_config(self, repo: Path, runner: CliRunner) -> None:
        (repo / "codeatlas.toml").write_text(
            "[check]\nfail_on_new_cycles = true\n", encoding="utf-8"
        )
        assert runner.invoke(main, ["baseline", str(repo)]).exit_code == 0
        introduce_cycle(repo)
        result = runner.invoke(main, ["check", str(repo), "--against-baseline"])
        assert result.exit_code == 3

    def test_explicit_baseline_path(self, repo: Path, runner: CliRunner, tmp_path: Path) -> None:
        custom = tmp_path / "ref.json"
        assert runner.invoke(
            main, ["baseline", str(repo), "--out", str(custom)]
        ).exit_code == 0
        introduce_cycle(repo)
        result = runner.invoke(
            main,
            ["check", str(repo), "--against-baseline", str(custom), "--fail-on-new-cycles"],
        )
        assert result.exit_code == 3
