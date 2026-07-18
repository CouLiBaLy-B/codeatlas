"""T003 — Golden test de la carte du dépôt (corpus python-demo)."""

from __future__ import annotations

from codeatlas.bridge.repomap import build_repomap
from codeatlas.config import Config

from .corpus import corpus_graph


def test_repomap_matches_golden(assert_golden) -> None:
    assert_golden("repomap.md", build_repomap(corpus_graph(), Config()))
