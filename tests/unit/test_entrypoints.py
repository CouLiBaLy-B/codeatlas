"""T035 — Reconnaisseurs de points d'entrée Python (main, click, routes web)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.insights.entrypoints import EntryPoint, detect_entrypoints
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def entrypoints() -> list[EntryPoint]:
    graph: CodeGraph = api.analyze(CORPUS)
    return list(detect_entrypoints(graph))


def by_kind(entrypoints: list[EntryPoint], kind: str) -> dict[str, EntryPoint]:
    return {e.node_id: e for e in entrypoints if e.kind == kind}


class TestMainGuard:
    def test_module_with_main_guard_detected(self, entrypoints: list[EntryPoint]) -> None:
        mains = by_kind(entrypoints, "main")
        assert "main/shopdemo.cli" in mains
        assert mains["main/shopdemo.cli"].framework == "python"

    def test_modules_without_guard_not_detected(self, entrypoints: list[EntryPoint]) -> None:
        assert "main/shopdemo.webapp" not in by_kind(entrypoints, "main")


class TestClickCommands:
    def test_click_command_detected(self, entrypoints: list[EntryPoint]) -> None:
        clis = by_kind(entrypoints, "cli")
        assert "main/shopdemo.cli.main" in clis
        assert clis["main/shopdemo.cli.main"].framework == "click"


class TestWebRoutes:
    def test_routes_detected_with_verb_and_path(self, entrypoints: list[EntryPoint]) -> None:
        routes = by_kind(entrypoints, "route")
        assert "main/shopdemo.webapp.list_products" in routes
        assert routes["main/shopdemo.webapp.list_products"].label == "GET /products"
        assert routes["main/shopdemo.webapp.create_product"].label == "POST /products"

    def test_every_entrypoint_carries_evidence(self, entrypoints: list[EntryPoint]) -> None:
        assert entrypoints, "aucun point d'entrée détecté sur le corpus"
        for entry in entrypoints:
            assert entry.evidence, f"détection sans indice : {entry}"


def test_detection_is_deterministic() -> None:
    graph = api.analyze(CORPUS)
    assert list(detect_entrypoints(graph)) == list(detect_entrypoints(graph))
