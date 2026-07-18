"""T006 — CLI `codeatlas export` : repomap, graphe JSON, budget, monorepo."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from codeatlas.cli import main

MONOREPO = Path(__file__).parents[2] / "examples" / "monorepo-demo"


class TestExport:
    def test_repomap_to_stdout(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["export", str(corpus)])
        assert result.exit_code == 0, result.output
        assert result.output.startswith("# Carte du dépôt")
        assert "Points d'entrée" in result.output

    def test_graph_format_is_canonical_ir_json(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["export", str(corpus), "--format", "graph"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ir_version"] == 1

    def test_out_file_written(self, corpus: Path, runner: CliRunner, tmp_path: Path) -> None:
        out = tmp_path / ".codeatlas" / "repomap.md"
        result = runner.invoke(main, ["export", str(corpus), "--out", str(out)])
        assert result.exit_code == 0
        assert out.read_text(encoding="utf-8").startswith("# Carte du dépôt")

    def test_budget_too_small_is_usage_error(self, corpus: Path, runner: CliRunner) -> None:
        result = runner.invoke(main, ["export", str(corpus), "--budget", "100"])
        assert result.exit_code == 2

    def test_monorepo_map_covers_subprojects(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["export", str(MONOREPO)])
        assert result.exit_code == 0, result.output
        for sub in ("frontend", "backend", "billing"):
            assert sub in result.output
