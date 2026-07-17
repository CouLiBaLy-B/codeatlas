"""Fixtures partagées des tests d'intégration."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def corpus() -> Path:
    return CORPUS
