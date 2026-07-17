"""T051 — Golden test du schéma AnalysisReport JSON (contrat cli.md)."""

from __future__ import annotations

import json
from pathlib import Path

from codeatlas import api
from codeatlas.config import Config
from codeatlas.report.json import report_to_json

from .corpus import corpus_graph


def _fresh_report(tmp_path: Path):
    from dataclasses import replace

    config = replace(Config(), site=replace(Config().site, enabled=False))
    return api.build_site(corpus_graph(), tmp_path / "out", config)


def test_report_json_matches_golden(tmp_path: Path, assert_golden) -> None:
    report = _fresh_report(tmp_path)
    assert report.duration_seconds == 0.0  # jamais renseignée hors CLI → déterministe
    assert_golden("report.json", report_to_json(report))


def test_report_json_schema_fields(tmp_path: Path) -> None:
    payload = json.loads(report_to_json(_fresh_report(tmp_path)))
    assert payload["report_version"] == 1
    assert set(payload["counts"]) == {
        "files_analyzed",
        "files_skipped",
        "nodes",
        "edges_certain",
        "edges_inferred",
    }
    assert payload["counts"]["edges_inferred"] >= 1  # l'appel getattr du corpus
    assert payload["skipped"][0]["path"] == "shopdemo/broken/invalid_syntax.py"


def test_report_json_is_canonical(tmp_path: Path) -> None:
    text = report_to_json(_fresh_report(tmp_path))
    assert text.endswith("\n")
    assert text == report_to_json(_fresh_report(tmp_path))
