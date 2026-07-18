"""Surveillance des sources via watchdog — injectable (les tests s'en passent)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

_IGNORED_PARTS = frozenset(
    {
        ".git",
        ".codeatlas",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)
_IGNORED_SUFFIXES = ("~", ".swp", ".swx", ".tmp", ".part")


def _is_noise(relative: Path) -> bool:
    if any(part in _IGNORED_PARTS for part in relative.parts):
        return True
    return relative.name.endswith(_IGNORED_SUFFIXES)


class FileWatcher:
    """Observe un dépôt et rappelle `callback(chemin relatif POSIX)` à chaque écriture."""

    def __init__(self, root: Path, callback: Callable[[str], None]) -> None:
        self.root = root.resolve()
        self._callback = callback
        self._observer: Any = None

    def _dispatch(self, raw_path: str) -> None:
        try:
            relative = Path(raw_path).resolve().relative_to(self.root)
        except ValueError:
            return
        if _is_noise(relative):
            return
        self._callback(relative.as_posix())

    def start(self) -> None:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        dispatch = self._dispatch

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event: Any) -> None:
                if getattr(event, "is_directory", False):
                    return
                for attribute in ("src_path", "dest_path"):
                    path = getattr(event, attribute, "")
                    if path:
                        dispatch(str(path))

        self._observer = Observer()
        self._observer.schedule(_Handler(), str(self.root), recursive=True)
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None
