"""T002 — Capture de la baseline : structure, canonicité, déterminisme (FR-001/003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.baseline.capture import BASELINE_VERSION, Baseline, capture
from codeatlas.baseline.store import BaselineError, from_json, to_json
from codeatlas.config import Config
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


@pytest.fixture(scope="module")
def baseline(graph: CodeGraph) -> Baseline:
    return capture(graph, Config())


class TestCaptureContent:
    def test_versions_recorded(self, baseline: Baseline) -> None:
        assert baseline.baseline_version == BASELINE_VERSION
        assert baseline.ir_version == 1

    def test_public_api_contains_expected_symbols(self, baseline: Baseline) -> None:
        ids = {entry.id for entry in baseline.public_api}
        assert "main/shopdemo.models.product.Product" in ids
        assert "main/shopdemo.legacy.pricing.audit_catalog" in ids
        # les symboles privés n'appartiennent pas à la surface publique
        assert "main/shopdemo.quality._forgotten_helper" not in ids

    def test_signatures_are_part_of_api_identity(self, baseline: Baseline) -> None:
        by_id = {entry.id: entry for entry in baseline.public_api}
        entry = by_id["main/shopdemo.models.product.Product.price_with_tax"]
        assert "rate: float = 0.2" in entry.signature

    def test_intentional_cycle_captured(self, baseline: Baseline) -> None:
        assert ["shopdemo.legacy", "shopdemo.services"] in [
            list(c) for c in baseline.package_cycles
        ]

    def test_inferred_calls_captured(self, baseline: Baseline) -> None:
        assert (
            "main/shopdemo.legacy.pricing.refresh_catalog_price",
            "main/shopdemo.services.catalog.CatalogService.price_of",
        ) in baseline.inferred_calls

    def test_dead_code_and_skipped_captured(self, baseline: Baseline) -> None:
        dead_ids = {identifier for identifier, _ in baseline.dead_code}
        assert "main/shopdemo.quality._forgotten_helper" in dead_ids
        assert tuple(
            path for path, _ in baseline.skipped
        ) == ("shopdemo/broken/invalid_syntax.py",)

    def test_metrics_present(self, baseline: Baseline) -> None:
        assert baseline.metric("files_analyzed") == 15
        assert 0 < baseline.metric("doc_coverage") <= 100
        assert baseline.metric("critical_symbols") >= 1  # tangled_pricing


class TestCanonicity:
    def test_double_capture_identical(self, graph: CodeGraph, baseline: Baseline) -> None:
        assert capture(graph, Config()) == baseline

    def test_json_roundtrip_and_determinism(self, baseline: Baseline) -> None:
        text = to_json(baseline)
        assert text.endswith("\n")
        assert to_json(from_json(text)) == text

    def test_no_timestamp_and_no_absolute_path(self, baseline: Baseline) -> None:
        text = to_json(baseline)
        assert "/home/" not in text
        for marker in ("2026", "time", "date"):
            assert f'"{marker}"' not in text


class TestVersionControl:
    def test_incompatible_baseline_version_rejected(self, baseline: Baseline) -> None:
        text = to_json(baseline).replace('"baseline_version": 1', '"baseline_version": 99')
        with pytest.raises(BaselineError, match="recapturer"):
            from_json(text)

    def test_incompatible_ir_version_rejected(self, baseline: Baseline) -> None:
        text = to_json(baseline).replace('"ir_version": 1', '"ir_version": 99')
        with pytest.raises(BaselineError, match="recapturer"):
            from_json(text)

    def test_invalid_json_rejected(self) -> None:
        with pytest.raises(BaselineError):
            from_json("{pas du json")
