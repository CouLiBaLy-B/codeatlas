"""T009 — Scénarios d'acceptation US1 : `codeatlas baseline` + `codeatlas diff`."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(CORPUS, target)
    return target


def run(runner: CliRunner, *args: str):
    return runner.invoke(main, list(args))


def introduce_cycle(repo: Path) -> None:
    product = repo / "shopdemo" / "models" / "product.py"
    product.write_text(
        product.read_text(encoding="utf-8")
        + "\nfrom shopdemo.services.catalog import CatalogService  # cycle volontaire\n",
        encoding="utf-8",
    )


def remove_public_api(repo: Path) -> None:
    pricing = repo / "shopdemo" / "legacy" / "pricing.py"
    text = pricing.read_text(encoding="utf-8")
    start = text.index("def audit_catalog")
    end = text.index("def refresh_catalog_price")
    pricing.write_text(text[:start] + text[end:], encoding="utf-8")


class TestScenario1DiffVide:
    def test_no_change_reports_empty_and_exit_0(self, repo: Path, runner: CliRunner) -> None:
        assert run(runner, "baseline", str(repo)).exit_code == 0
        result = run(runner, "diff", str(repo))
        assert result.exit_code == 0, result.output
        assert "Aucun changement architectural" in result.output


class TestScenario2CycleApparu:
    def test_new_cycle_listed_with_packages(self, repo: Path, runner: CliRunner) -> None:
        assert run(runner, "baseline", str(repo)).exit_code == 0
        introduce_cycle(repo)
        result = run(runner, "diff", str(repo))
        assert result.exit_code == 0
        assert "shopdemo.models" in result.output
        assert "shopdemo.services" in result.output
        assert "apparu" in result.output.lower()


class TestScenario3ApiDisparue:
    def test_removed_api_listed(self, repo: Path, runner: CliRunner) -> None:
        assert run(runner, "baseline", str(repo)).exit_code == 0
        remove_public_api(repo)
        result = run(runner, "diff", str(repo))
        assert result.exit_code == 0
        assert "audit_catalog" in result.output
        assert "disparu" in result.output.lower()


class TestScenario4Determinisme:
    def test_double_diff_identical(self, repo: Path, runner: CliRunner) -> None:
        assert run(runner, "baseline", str(repo)).exit_code == 0
        introduce_cycle(repo)
        first = run(runner, "diff", str(repo)).output
        second = run(runner, "diff", str(repo)).output
        assert first == second


class TestErreursUsage:
    def test_missing_baseline_exit_2(self, repo: Path, runner: CliRunner) -> None:
        result = run(runner, "diff", str(repo))
        assert result.exit_code == 2
        assert "codeatlas baseline" in result.output

    def test_incompatible_baseline_exit_2(self, repo: Path, runner: CliRunner) -> None:
        assert run(runner, "baseline", str(repo)).exit_code == 0
        target = repo / ".codeatlas" / "baseline.json"
        target.write_text(
            target.read_text(encoding="utf-8").replace(
                '"baseline_version": 1', '"baseline_version": 99'
            ),
            encoding="utf-8",
        )
        result = run(runner, "diff", str(repo))
        assert result.exit_code == 2
        assert "recapturer" in result.output


class TestFormatsEtArchives:
    def test_json_format_is_parseable(self, repo: Path, runner: CliRunner) -> None:
        assert run(runner, "baseline", str(repo)).exit_code == 0
        introduce_cycle(repo)
        result = run(runner, "diff", str(repo), "--format", "json")
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "categories" in payload

    def test_archive_writes_history_file(self, repo: Path, runner: CliRunner) -> None:
        result = run(runner, "baseline", str(repo), "--archive", "v1")
        assert result.exit_code == 0
        assert (repo / ".codeatlas" / "history" / "v1.json").is_file()

    def test_baseline_capture_is_deterministic(self, repo: Path, runner: CliRunner) -> None:
        assert run(runner, "baseline", str(repo)).exit_code == 0
        first = (repo / ".codeatlas" / "baseline.json").read_bytes()
        assert run(runner, "baseline", str(repo)).exit_code == 0
        assert (repo / ".codeatlas" / "baseline.json").read_bytes() == first
