"""T002 — Carte du dépôt : priorisation, budget, omissions explicites (FR-001/002/003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.bridge.repomap import build_repomap
from codeatlas.config import Config
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


class TestContent:
    def test_header_and_entrypoints_always_present(self, graph: CodeGraph) -> None:
        text = build_repomap(graph, Config())
        assert "python-demo" in text
        assert "Points d'entrée" in text
        assert "GET /products" in text

    def test_public_api_with_signatures_and_doc(self, graph: CodeGraph) -> None:
        text = build_repomap(graph, Config())
        assert "price_with_tax(rate: float = 0.2) -> float" in text
        assert "Un produit physique du catalogue." in text  # résumé de doc EXISTANTE
        assert "_forgotten_helper" not in text  # privé : hors surface publique

    def test_entry_modules_come_before_others(self, graph: CodeGraph) -> None:
        text = build_repomap(graph, Config())
        # cli et webapp portent les points d'entrée → avant storage.repo
        assert text.index("shopdemo.cli") < text.index("shopdemo.storage.repo")
        assert text.index("shopdemo.webapp") < text.index("shopdemo.storage.repo")


class TestExhaustiveness:
    def test_all_public_symbols_present_when_budget_allows(self, graph: CodeGraph) -> None:
        """SC-001 : 100 % des APIs publiques figurent dans la carte (budget suffisant)."""
        from codeatlas.ir.model import NodeKind, Visibility

        text = build_repomap(graph, Config(), budget=100_000)
        missing = [
            node.name
            for node in graph.iter_nodes()
            if node.kind
            in (
                NodeKind.CLASS,
                NodeKind.INTERFACE,
                NodeKind.ENUM,
                NodeKind.FUNCTION,
                NodeKind.METHOD,
            )
            and node.visibility is Visibility.PUBLIC
            and node.name not in text
        ]
        assert missing == []


class TestBudget:
    def test_full_map_within_default_budget_no_omission(self, graph: CodeGraph) -> None:
        text = build_repomap(graph, Config())
        assert len(text) <= Config().export.budget
        assert "Omis (budget)" not in text

    def test_small_budget_truncates_whole_modules_and_says_so(self, graph: CodeGraph) -> None:
        text = build_repomap(graph, Config(), budget=2600)
        assert len(text) <= 2600
        assert "Omis (budget)" in text

    def test_budget_below_minimum_is_an_error(self, graph: CodeGraph) -> None:
        with pytest.raises(ValueError, match="budget"):
            build_repomap(graph, Config(), budget=500)


class TestDeterminism:
    def test_double_build_identical(self, graph: CodeGraph) -> None:
        assert build_repomap(graph, Config()) == build_repomap(graph, Config())
