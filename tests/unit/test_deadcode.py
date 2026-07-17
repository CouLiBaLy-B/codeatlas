"""T045 — Code probablement mort : atteignabilité + références, confiance (R7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.insights.deadcode import DeadCodeCandidate, find_dead_code
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


@pytest.fixture(scope="module")
def candidates(graph: CodeGraph) -> dict[str, DeadCodeCandidate]:
    return {c.node_id: c for c in find_dead_code(graph)}


class TestIntentionalDeadCode:
    def test_private_dead_helper_high_confidence(
        self, candidates: dict[str, DeadCodeCandidate]
    ) -> None:
        entry = candidates["main/shopdemo.quality._forgotten_helper"]
        assert entry.confidence == "high"

    def test_public_dead_function_lower_confidence(
        self, candidates: dict[str, DeadCodeCandidate]
    ) -> None:
        entry = candidates["main/shopdemo.quality.forgotten_public_api"]
        assert entry.confidence == "medium"

    def test_private_unused_method_detected(
        self, candidates: dict[str, DeadCodeCandidate]
    ) -> None:
        assert "main/shopdemo.models.product.Product._rounded" in candidates


class TestLiveCodeNeverFlagged:
    def test_entrypoints_are_roots(self, candidates: dict[str, DeadCodeCandidate]) -> None:
        assert "main/shopdemo.cli.main" not in candidates
        assert "main/shopdemo.webapp.list_products" not in candidates

    def test_reachable_code_not_flagged(self, candidates: dict[str, DeadCodeCandidate]) -> None:
        assert "main/shopdemo.services.orders.OrderService.place" not in candidates
        assert "main/shopdemo.storage.repo.InMemoryRepo.find" not in candidates

    def test_inferred_call_target_not_flagged(
        self, candidates: dict[str, DeadCodeCandidate]
    ) -> None:
        # price_of est appelé (dont via getattr → inferred) : vivant
        assert "main/shopdemo.services.catalog.CatalogService.price_of" not in candidates

    def test_dunder_methods_never_flagged(self, candidates: dict[str, DeadCodeCandidate]) -> None:
        assert not any(node_id.endswith("__init__") for node_id in candidates)


class TestEvidence:
    def test_every_candidate_has_reason(self, candidates: dict[str, DeadCodeCandidate]) -> None:
        assert candidates, "aucun candidat code mort sur le corpus"
        for candidate in candidates.values():
            assert candidate.reason


def test_determinism(graph: CodeGraph) -> None:
    assert find_dead_code(graph) == find_dead_code(graph)
