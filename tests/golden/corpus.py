"""Graphe partagé du corpus python-demo pour les golden tests."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from codeatlas import api
from codeatlas.ir.model import CodeGraph

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@lru_cache(maxsize=1)
def corpus_graph() -> CodeGraph:
    return api.analyze(CORPUS)
