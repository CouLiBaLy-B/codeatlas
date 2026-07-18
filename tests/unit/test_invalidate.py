"""T016 — Analyse incrémentale par unités de sous-projet (US3, FR-010).

L'invariant central : une analyse incrémentale après modification produit un
graphe STRICTEMENT identique à une analyse complète à froid (convergence).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.config import load_config
from codeatlas.ir.serialize import to_json
from codeatlas.serve.invalidate import IncrementalAnalyzer

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(CORPUS, target)
    return target


def _monorepo(tmp_path: Path) -> Path:
    root = tmp_path / "mono"
    for sub, module in (("svc-a", "alpha"), ("svc-b", "beta")):
        (root / sub).mkdir(parents=True)
        (root / sub / "pyproject.toml").write_text(
            f'[project]\nname = "{sub}"\n', encoding="utf-8"
        )
        (root / sub / f"{module}.py").write_text(
            f'"""Module {module}."""\n\n\ndef {module}() -> int:\n    return 1\n',
            encoding="utf-8",
        )
    return root


def test_full_analysis_matches_api_analyze(workspace: Path) -> None:
    analyzer = IncrementalAnalyzer(workspace, load_config(workspace))
    assert to_json(analyzer.analyze()) == to_json(api.analyze(workspace))


def test_incremental_after_edit_equals_cold_analysis(workspace: Path) -> None:
    analyzer = IncrementalAnalyzer(workspace, load_config(workspace))
    analyzer.analyze()
    target = workspace / "shopdemo" / "models" / "product.py"
    target.write_text(
        target.read_text(encoding="utf-8")
        + '\n\ndef fresh_helper() -> str:\n    """Nouvelle fonction."""\n    return "ok"\n',
        encoding="utf-8",
    )
    incremental = analyzer.analyze(changed={"shopdemo/models/product.py"})
    assert "fresh_helper" in to_json(incremental)
    assert to_json(incremental) == to_json(api.analyze(workspace))


def test_incremental_after_delete_equals_cold_analysis(workspace: Path) -> None:
    analyzer = IncrementalAnalyzer(workspace, load_config(workspace))
    analyzer.analyze()
    (workspace / "shopdemo" / "quality.py").unlink()
    incremental = analyzer.analyze(changed={"shopdemo/quality.py"})
    assert to_json(incremental) == to_json(api.analyze(workspace))


def test_unrelated_file_change_is_harmless(workspace: Path) -> None:
    analyzer = IncrementalAnalyzer(workspace, load_config(workspace))
    before = to_json(analyzer.analyze())
    (workspace / "README.md").write_text("# doc\n", encoding="utf-8")
    assert to_json(analyzer.analyze(changed={"README.md"})) == before


def test_monorepo_only_owning_subproject_is_reanalyzed(tmp_path: Path) -> None:
    root = _monorepo(tmp_path)
    analyzer = IncrementalAnalyzer(root, load_config(root))
    analyzer.analyze()
    assert analyzer.affected_subprojects({"svc-a/alpha.py"}) == ["svc-a"]
    (root / "svc-a" / "alpha.py").write_text(
        '"""Module alpha."""\n\n\ndef alpha_two() -> int:\n    return 2\n', encoding="utf-8"
    )
    incremental = analyzer.analyze(changed={"svc-a/alpha.py"})
    assert to_json(incremental) == to_json(api.analyze(root))


def test_manifest_change_is_structural(workspace: Path) -> None:
    analyzer = IncrementalAnalyzer(workspace, load_config(workspace))
    assert analyzer.is_structural("pyproject.toml")
    assert analyzer.is_structural("codeatlas.toml")
    assert analyzer.is_structural("svc/package.json")
    assert not analyzer.is_structural("shopdemo/models/product.py")
