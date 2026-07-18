"""T077 — SC-001 : dépôt de ~50 000 lignes documenté en moins de 30 secondes.

Machine de référence : runner GitHub Actions ubuntu-latest standard.
Marqué `slow` : exécuté à la demande (pytest -m slow), pas dans la CI par défaut.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from codeatlas.cli import main

MODULE_TEMPLATE = '''"""Module généré n°{index} du corpus synthétique."""


class Service{index}:
    """Service métier n°{index}."""

    def __init__(self, repo: object) -> None:
        self.repo = repo
        self.cache: dict[str, float] = {{}}

{methods}


class Repository{index}:
    """Dépôt n°{index}."""

    def __init__(self) -> None:
        self.items: dict[str, float] = {{}}

{methods_repo}


def helper_{index}(value: float, flag: bool = False) -> float:
    """Fonction utilitaire n°{index}."""
    if flag and value > 10:
        return value * 2
    return value
'''

METHOD_TEMPLATE = '''    def operation_{m}(self, amount: float, rate: float = 0.2) -> float:
        """Opération n°{m} : calcule un montant ajusté."""
        result = amount
        if rate > 0.5:
            result *= 1 + rate
        elif rate > 0.1:
            result *= 1.1
        for _step in range(3):
            if result > 1000:
                result *= 0.99
        return round(result, 2)
'''


def _generate_corpus(root: Path, target_lines: int = 50_000) -> int:
    """Corpus Python synthétique : ~250 lignes/fichier (taille de fichier réaliste)."""
    package = root / "bigapp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"""Corpus synthétique."""\n', encoding="utf-8")
    total = 0
    index = 0
    while total < target_lines:
        methods = "\n".join(METHOD_TEMPLATE.format(m=m) for m in range(10))
        methods_repo = "\n".join(METHOD_TEMPLATE.format(m=m + 10) for m in range(10))
        content = MODULE_TEMPLATE.format(
            index=index, methods=methods, methods_repo=methods_repo
        )
        subpackage = package / f"domain{index % 20}"
        subpackage.mkdir(exist_ok=True)
        init = subpackage / "__init__.py"
        if not init.exists():
            init.write_text('"""Sous-package."""\n', encoding="utf-8")
        (subpackage / f"module{index}.py").write_text(content, encoding="utf-8")
        total += content.count("\n")
        index += 1
    return total


@pytest.mark.slow
def test_baseline_diff_gate_under_10_seconds(tmp_path: Path) -> None:
    """SC-003 (feature 002) : cycle baseline → diff → gate < 10 s sur ~50 k lignes."""
    corpus = tmp_path / "bigrepo"
    _generate_corpus(corpus)
    runner = CliRunner()
    assert runner.invoke(main, ["baseline", str(corpus)]).exit_code == 0

    started = time.monotonic()
    assert runner.invoke(main, ["diff", str(corpus)]).exit_code == 0
    assert (
        runner.invoke(
            main, ["check", str(corpus), "--against-baseline", "--fail-on-new-cycles"]
        ).exit_code
        == 0
    )
    elapsed = time.monotonic() - started
    assert elapsed < 10, f"diff + gate en {elapsed:.1f}s (> 10s) — SC-003 feature 002"


@pytest.mark.slow
def test_50k_lines_documented_under_30_seconds(tmp_path: Path) -> None:
    corpus = tmp_path / "bigrepo"
    lines = _generate_corpus(corpus)
    assert lines >= 50_000

    out = tmp_path / "out"
    started = time.monotonic()
    result = CliRunner().invoke(main, ["build", str(corpus), "--out", str(out), "--quiet"])
    elapsed = time.monotonic() - started

    assert result.exit_code == 0, result.output
    assert (out / "site" / "index.html").is_file()
    assert elapsed < 30, f"génération en {elapsed:.1f}s (> 30s) pour {lines} lignes — SC-001"
