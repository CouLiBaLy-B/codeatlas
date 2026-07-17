"""Mécanique des golden files : comparaison stricte, mise à jour via UPDATE_GOLDEN=1."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture()
def assert_golden():
    def _assert(name: str, actual: str) -> None:
        path = DATA_DIR / name
        if os.environ.get("UPDATE_GOLDEN") == "1":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8", newline="\n")
            pytest.skip(f"golden {name} mis à jour")
        assert path.is_file(), (
            f"golden manquant : {name} — lancer UPDATE_GOLDEN=1 pytest puis relire le fichier"
        )
        assert actual == path.read_text(encoding="utf-8"), f"écart avec le golden {name}"

    return _assert
