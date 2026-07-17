"""T052 — Scénario d'acceptation US4 : `codeatlas check` en pipeline CI."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from codeatlas.cli import main


class TestExitCodes:
    def test_violated_threshold_exits_3(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check", str(corpus), "--min-doc-coverage", "99"])
        assert result.exit_code == 3

    def test_met_threshold_exits_0(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check", str(corpus), "--min-doc-coverage", "10"])
        assert result.exit_code == 0, result.output

    def test_no_threshold_exits_0(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check", str(corpus)])
        assert result.exit_code == 0

    def test_cycle_regression_detected(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["check", str(corpus), "--max-package-cycles", "0"])
        assert result.exit_code == 3
        assert "max-package-cycles" in result.output


class TestReport:
    def test_json_report_contains_check_results(
        self, corpus: Path, runner: CliRunner, tmp_path: Path
    ) -> None:
        report_path = tmp_path / "report.json"
        result = runner.invoke(
            main,
            [
                "check",
                str(corpus),
                "--min-doc-coverage",
                "99",
                "--json-report",
                str(report_path),
            ],
        )
        assert result.exit_code == 3
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        checks = {c["name"]: c for c in payload["checks"]}
        assert checks["min-doc-coverage"]["passed"] is False
        assert checks["min-doc-coverage"]["threshold"] == 99

    def test_thresholds_from_config_file(
        self, corpus: Path, runner: CliRunner, tmp_path: Path
    ) -> None:
        config = tmp_path / "codeatlas.toml"
        config.write_text("[check]\nmin_doc_coverage = 99\n", encoding="utf-8")
        result = runner.invoke(main, ["check", str(corpus), "--config", str(config)])
        assert result.exit_code == 3

    def test_cli_overrides_config_file(
        self, corpus: Path, runner: CliRunner, tmp_path: Path
    ) -> None:
        config = tmp_path / "codeatlas.toml"
        config.write_text("[check]\nmin_doc_coverage = 99\n", encoding="utf-8")
        result = runner.invoke(
            main,
            ["check", str(corpus), "--config", str(config), "--min-doc-coverage", "10"],
        )
        assert result.exit_code == 0, result.output
