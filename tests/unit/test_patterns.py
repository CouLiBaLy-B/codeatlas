"""T059 — Détection des design patterns + non-détection des contre-exemples (SC-008)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.insights.patterns import PatternDetection, detect_patterns
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "layered-demo"


@pytest.fixture(scope="module")
def graph() -> CodeGraph:
    return api.analyze(CORPUS)


@pytest.fixture(scope="module")
def detections(graph: CodeGraph) -> dict[str, PatternDetection]:
    return {d.class_id: d for d in detect_patterns(graph)}


def pattern_of(detections: dict[str, PatternDetection], qualname: str) -> str | None:
    entry = detections.get(f"main/{qualname}")
    return entry.pattern if entry else None


class TestTruePositives:
    def test_singleton(self, detections: dict[str, PatternDetection]) -> None:
        assert pattern_of(detections, "webshop.infra.database.DatabaseConnection") == "singleton"

    def test_factory(self, detections: dict[str, PatternDetection]) -> None:
        assert pattern_of(detections, "webshop.domain.factory.ObserverFactory") == "factory"

    def test_observer(self, detections: dict[str, PatternDetection]) -> None:
        assert pattern_of(detections, "webshop.domain.events.EventBus") == "observer"

    def test_adapter(self, detections: dict[str, PatternDetection]) -> None:
        assert pattern_of(detections, "webshop.infra.payments.StripeAdapter") == "adapter"

    def test_decorator(self, detections: dict[str, PatternDetection]) -> None:
        assert pattern_of(detections, "webshop.domain.models.DiscountedPrice") == "decorator"


class TestCounterExamples:
    def test_name_alone_is_not_a_singleton(self, detections: dict[str, PatternDetection]) -> None:
        assert pattern_of(detections, "webshop.infra.database.SingletonRegistry") is None

    def test_create_method_returning_scalar_is_not_a_factory(
        self, detections: dict[str, PatternDetection]
    ) -> None:
        assert pattern_of(detections, "webshop.domain.factory.ReportBuilder") is None

    def test_notify_without_subscribers_is_not_an_observer(
        self, detections: dict[str, PatternDetection]
    ) -> None:
        assert pattern_of(detections, "webshop.domain.events.Notifier") is None

    def test_plain_inheritance_is_not_a_decorator(
        self, detections: dict[str, PatternDetection]
    ) -> None:
        # EmailObserver hérite d'OrderObserver sans l'envelopper
        assert pattern_of(detections, "webshop.domain.factory.EmailObserver") is None


class TestEvidence:
    def test_every_detection_has_evidence(self, detections: dict[str, PatternDetection]) -> None:
        assert detections
        for detection in detections.values():
            assert detection.evidence, f"détection sans indice : {detection}"


def test_determinism(graph: CodeGraph) -> None:
    assert detect_patterns(graph) == detect_patterns(graph)
