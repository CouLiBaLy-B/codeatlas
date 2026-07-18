"""T014 — Parcours de lecture : entrées d'abord, puis couches hautes → basses."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.config import Config
from codeatlas.insights.tour import reading_tour
from codeatlas.ir.model import CodeGraph

LAYERED = Path(__file__).parents[2] / "examples" / "layered-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(LAYERED)


class TestOrder:
    def test_entry_module_comes_first(self, graph: CodeGraph) -> None:
        steps = reading_tour(graph, Config())
        assert steps[0].module == "webshop.api.routes"
        assert "entrée" in steps[0].reason

    def test_layers_descend_from_api_to_infra(self, graph: CodeGraph) -> None:
        steps = reading_tour(graph, Config())
        order = [step.module for step in steps]
        domain_first = min(
            i for i, m in enumerate(order) if m.startswith("webshop.domain")
        )
        infra_first = min(i for i, m in enumerate(order) if m.startswith("webshop.infra"))
        assert domain_first < infra_first

    def test_every_module_visited_once(self, graph: CodeGraph) -> None:
        steps = reading_tour(graph, Config())
        modules = [step.module for step in steps]
        assert len(modules) == len(set(modules))
        assert "webshop.infra.legacy_bridge" in modules  # aucun module oublié

    def test_steps_reference_doc_pages(self, graph: CodeGraph) -> None:
        steps = reading_tour(graph, Config())
        assert all(step.page.endswith(".md") for step in steps)


def test_determinism(graph: CodeGraph) -> None:
    assert reading_tour(graph, Config()) == reading_tour(graph, Config())
