"""T003 — Golden test du JSON de baseline (contrat baseline-schema.md)."""

from __future__ import annotations

import json

from codeatlas.baseline.capture import capture
from codeatlas.baseline.store import to_json
from codeatlas.config import Config

from .corpus import corpus_graph


def test_baseline_json_matches_golden(assert_golden) -> None:
    assert_golden("baseline.json", to_json(capture(corpus_graph(), Config())))


def test_baseline_json_schema_fields() -> None:
    payload = json.loads(to_json(capture(corpus_graph(), Config())))
    assert set(payload) == {
        "baseline_version",
        "ir_version",
        "root",
        "subprojects",
        "public_api",
        "package_cycles",
        "layer_violations",
        "inferred_calls",
        "dead_code",
        "service_deps",
        "skipped",
        "metrics",
    }
    assert payload["public_api"] == sorted(payload["public_api"], key=lambda e: e["id"])
