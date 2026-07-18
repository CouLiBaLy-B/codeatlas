"""T017 — Session d'atelier (US3) : debounce, tolérance, jeton, convergence."""

from __future__ import annotations

import filecmp
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.config import SiteCfg, load_config
from codeatlas.serve.session import WorkshopSession

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(CORPUS, target)
    return target


def _session(workspace: Path, tmp_path: Path, events: list[dict] | None = None):
    config = replace(load_config(workspace), site=SiteCfg(enabled=False))
    return WorkshopSession(
        workspace,
        config,
        workdir=tmp_path / "atelier",
        on_event=events.append if events is not None else None,
    )


def test_initial_build_emits_event_and_site(workspace: Path, tmp_path: Path) -> None:
    events: list[dict] = []
    session = _session(workspace, tmp_path, events)
    session.build()
    assert session.build_token == 1
    assert (session.out / "docs" / "index.md").is_file()
    builds = [e for e in events if e["event"] == "build"]
    assert builds and builds[0]["trigger"] == "initial" and builds[0]["elements"] > 0


def test_debounce_groups_bursts_and_last_version_wins(
    workspace: Path, tmp_path: Path
) -> None:
    events: list[dict] = []
    session = _session(workspace, tmp_path, events)
    session.build()
    target = workspace / "shopdemo" / "quality.py"
    base = target.read_text(encoding="utf-8")
    target.write_text(base + "\n\ndef step_one() -> None:\n    pass\n", encoding="utf-8")
    session.notify_change("shopdemo/quality.py")
    target.write_text(base + "\n\ndef step_two() -> None:\n    pass\n", encoding="utf-8")
    session.notify_change("shopdemo/quality.py")  # rafale sur le même fichier
    assert session.flush() is True
    reloads = [e for e in events if e["event"] == "reload"]
    assert len(reloads) == 1  # une seule régénération pour la rafale
    page = (session.out / "docs" / "modules" / "shopdemo.quality.md").read_text(
        encoding="utf-8"
    )
    assert "step_two" in page and "step_one" not in page  # la dernière version fait foi
    assert session.build_token == 2


def test_flush_without_pending_changes_does_nothing(workspace: Path, tmp_path: Path) -> None:
    session = _session(workspace, tmp_path)
    session.build()
    assert session.flush() is False
    assert session.build_token == 1


def test_broken_file_keeps_session_alive_with_warning(
    workspace: Path, tmp_path: Path
) -> None:
    events: list[dict] = []
    session = _session(workspace, tmp_path, events)
    session.build()
    target = workspace / "shopdemo" / "quality.py"
    original = target.read_text(encoding="utf-8")
    target.write_text("def broken(:\n", encoding="utf-8")
    session.notify_change("shopdemo/quality.py")
    assert session.flush() is True  # la session survit (principe IV)
    assert any(w["path"] == "shopdemo/quality.py" for w in session.warnings)
    assert any(
        e["event"] == "warning" and e["path"] == "shopdemo/quality.py" for e in events
    )
    assert (session.out / "docs" / "index.md").is_file()  # le site reste servi

    target.write_text(original, encoding="utf-8")
    session.notify_change("shopdemo/quality.py")
    session.flush()
    assert all(w["path"] != "shopdemo/quality.py" for w in session.warnings)


def test_build_token_is_monotonic(workspace: Path, tmp_path: Path) -> None:
    session = _session(workspace, tmp_path)
    session.build()
    tokens = [session.build_token]
    for index in range(2):
        target = workspace / "shopdemo" / "quality.py"
        target.write_text(
            target.read_text(encoding="utf-8") + f"\n\ndef gen_{index}() -> None:\n    pass\n",
            encoding="utf-8",
        )
        session.notify_change("shopdemo/quality.py")
        session.flush()
        tokens.append(session.build_token)
    assert tokens == sorted(tokens) and len(set(tokens)) == len(tokens)


def test_session_converges_to_cold_build(workspace: Path, tmp_path: Path) -> None:
    """Invariant : après N cycles incrémentaux, sortie ≡ build complet à froid."""
    session = _session(workspace, tmp_path)
    session.build()
    target = workspace / "shopdemo" / "models" / "product.py"
    target.write_text(
        target.read_text(encoding="utf-8")
        + '\n\ndef converge() -> str:\n    """Ajout."""\n    return "ok"\n',
        encoding="utf-8",
    )
    session.notify_change("shopdemo/models/product.py")
    session.flush()

    cold = tmp_path / "cold"
    config = replace(load_config(workspace), site=SiteCfg(enabled=False))
    api.build_site(api.analyze(workspace, config), cold, config, source_root=workspace)

    comparison = filecmp.dircmp(session.out / "docs", cold / "docs")
    differences: list[str] = []

    def _collect(cmp) -> None:
        differences.extend(cmp.diff_files + cmp.left_only + cmp.right_only + cmp.funny_files)
        for sub in cmp.subdirs.values():
            _collect(sub)

    _collect(comparison)
    assert differences == []
