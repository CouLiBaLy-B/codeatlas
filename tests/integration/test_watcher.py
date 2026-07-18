"""T029 — Watcher réel (watchdog) : événements fichiers → callback, bruit filtré."""

from __future__ import annotations

import time
from pathlib import Path

from codeatlas.serve.watcher import FileWatcher


def _wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_watcher_reports_relative_posix_paths(tmp_path: Path) -> None:
    seen: list[str] = []
    watcher = FileWatcher(tmp_path, seen.append)
    watcher.start()
    try:
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
        assert _wait_for(lambda: "pkg/mod.py" in seen), seen
    finally:
        watcher.stop()


def test_reading_a_watched_file_triggers_nothing(tmp_path: Path) -> None:
    """Régression : la régénération RELIT les sources surveillées — ces lectures
    (événements watchdog `opened`/`closed_no_write`) ne doivent jamais déclencher
    de rebuild, sinon la session boucle sur elle-même."""
    target = tmp_path / "mod.py"
    target.write_text("x = 1\n", encoding="utf-8")
    seen: list[str] = []
    watcher = FileWatcher(tmp_path, seen.append)
    watcher.start()
    try:
        for _ in range(3):
            target.read_text(encoding="utf-8")  # lecture pure, aucune écriture
        time.sleep(1.0)  # laisse largement le temps aux événements inotify
        assert seen == []
        target.write_text("x = 2\n", encoding="utf-8")
        assert _wait_for(lambda: "mod.py" in seen), seen  # les écritures, elles, passent
    finally:
        watcher.stop()


def test_watcher_filters_noise(tmp_path: Path) -> None:
    seen: list[str] = []
    watcher = FileWatcher(tmp_path, seen.append)
    watcher.start()
    try:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "index").write_text("x", encoding="utf-8")
        (tmp_path / "notes.py.swp").write_text("x", encoding="utf-8")
        (tmp_path / "real.py").write_text("x = 1\n", encoding="utf-8")
        assert _wait_for(lambda: "real.py" in seen), seen
        assert all(not p.startswith(".git/") for p in seen)
        assert "notes.py.swp" not in seen
    finally:
        watcher.stop()
