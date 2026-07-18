"""Session d'atelier (US3) : régénération incrémentale, tolérance, jeton de build.

Cycle : notify_change (thread watcher) accumule → flush (worker debounce) draine
et régénère. Une erreur d'analyse ne tue JAMAIS la session (principe IV) : le
site précédent reste servi et l'échec devient un événement structuré. Invariant :
à sources identiques, la sortie de la session est identique octet pour octet à un
build complet à froid (testé).
"""

from __future__ import annotations

import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from codeatlas.api import CodeAtlasError, build_site
from codeatlas.config import Config, load_config
from codeatlas.serve.invalidate import IncrementalAnalyzer

DEBOUNCE_SECONDS = 0.3


class WorkshopSession:
    """Cycle de vie du mode atelier — indépendant du serveur HTTP et du watcher."""

    def __init__(
        self,
        root: Path,
        config: Config | None = None,
        *,
        workdir: Path | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self._explicit_config = config is not None
        self.config = config if config is not None else load_config(self.root)
        self.workdir = (
            Path(workdir)
            if workdir is not None
            else Path(tempfile.mkdtemp(prefix="codeatlas-atelier-"))
        )
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.out = self.workdir / "out"
        self.build_token = 0
        self.warnings: list[dict[str, str]] = []
        self._on_event = on_event
        self._analyzer = IncrementalAnalyzer(self.root, self.config)
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self.wakeup = threading.Event()  # signal pour le worker de debounce
        self.stopped = False
        # renseignés par api.serve_docs (le serveur/watcher restent optionnels)
        self.server: Any = None
        self.watcher: Any = None
        self.threads: list[threading.Thread] = []

    # -- événements --------------------------------------------------------------

    def _emit(self, event: dict[str, Any]) -> None:
        if self._on_event is not None:
            self._on_event(event)

    @property
    def site_dir(self) -> Path:
        return self.out / "site"

    # -- cycle de génération -------------------------------------------------------

    def build(self, changed: set[str] | None = None, trigger: str = "initial") -> bool:
        """(Re)génère la documentation ; False si l'analyse a totalement échoué."""
        started = time.monotonic()
        try:
            graph = self._analyzer.analyze(changed)
        except CodeAtlasError as exc:
            self._emit(
                {"event": "warning", "path": trigger, "reason": str(exc), "scope": "repo"}
            )
            return False  # l'ancien site reste servi
        report = build_site(graph, self.out, self.config, source_root=self.root)
        self.build_token += 1
        previous = {w["path"] for w in self.warnings}
        self.warnings = [
            {"path": s.path, "reason": s.reason, "scope": "file"} for s in graph.skipped
        ] + [
            {"path": w.where, "reason": w.detail or w.code, "scope": "site"}
            for w in report.warnings
        ]
        self._emit(
            {
                "event": "build" if self.build_token == 1 else "reload",
                "trigger": trigger,
                "elements": len(graph.nodes),
                "warnings": len(self.warnings),
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
        for warning in self.warnings:
            if warning["path"] not in previous:
                self._emit({"event": "warning", **warning})
        return True

    def notify_change(self, path: str | Path) -> None:
        """Thread-safe ; chemin absolu ou relatif au dépôt (POSIX)."""
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                rel = candidate.resolve().relative_to(self.root).as_posix()
            except ValueError:
                return  # hors du dépôt surveillé
        else:
            rel = candidate.as_posix()
        with self._lock:
            self._pending.add(rel)
        self.wakeup.set()

    def flush(self) -> bool:
        """Draine les changements en attente et régénère ; False si rien à faire."""
        with self._lock:
            pending, self._pending = self._pending, set()
        self.wakeup.clear()
        if not pending:
            return False
        trigger = sorted(pending)[0]
        if any(self._analyzer.is_structural(path) for path in pending):
            # la carte des sous-projets (ou la config) a pu changer : repartir à zéro
            if not self._explicit_config:
                self.config = load_config(self.root)
            self._analyzer = IncrementalAnalyzer(self.root, self.config)
            self.build(None, trigger=trigger)
        else:
            self.build(pending, trigger=trigger)
        return True

    # -- arrêt ---------------------------------------------------------------------

    def stop(self) -> None:
        """Arrêt propre : watcher, serveur, worker — idempotent."""
        self.stopped = True
        self.wakeup.set()
        if self.watcher is not None:
            self.watcher.stop()
            self.watcher = None
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        for thread in self.threads:
            thread.join(timeout=2)
        self.threads = []
