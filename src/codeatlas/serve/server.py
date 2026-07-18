"""Serveur HTTP du mode atelier — 127.0.0.1 uniquement, bibliothèque standard.

Le script d'auto-rechargement (polling du jeton de build) est injecté À LA VOLÉE
dans les réponses HTML : il n'existe jamais dans les artefacts sur disque, qui
restent déterministes et committables (constitution I).
"""

from __future__ import annotations

import errno
import threading
from collections.abc import Callable
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from codeatlas.api import CodeAtlasError

TOKEN_ROUTE = "/__atlas_build__"
RELOAD_ROUTE = "/__atlas_reload__.js"

_RELOAD_JS = (
    "/* Auto-rechargement du mode atelier - injecte par le serveur local uniquement. */\n"
    '(function () {\n'
    '  "use strict";\n'
    "  var current = null;\n"
    "  function poll() {\n"
    '    fetch("' + TOKEN_ROUTE + '", { cache: "no-store" })\n'
    "      .then(function (r) { return r.text(); })\n"
    "      .then(function (token) {\n"
    "        if (current === null) current = token;\n"
    "        else if (token !== current) window.location.reload();\n"
    "      })\n"
    "      .catch(function () { /* serveur arrete : silencieux */ });\n"
    "  }\n"
    "  setInterval(poll, 1000);\n"
    "})();\n"
)

_INJECTION = b'<script src="' + RELOAD_ROUTE.encode("ascii") + b'"></script></body>'


class PortInUseError(CodeAtlasError):
    """Le port demandé est déjà occupé (exit 4 côté CLI)."""

    def __init__(self, port: int) -> None:
        super().__init__(f"le port {port} est déjà utilisé — choisissez --port")
        self.port = port


def _make_handler(site_dir: Path, token_provider: Callable[[], str]) -> type:
    class _Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(site_dir), **kwargs)

        def log_message(self, format: str, *args: object) -> None:
            pass  # jamais de log HTTP sur stderr (les événements passent par --json)

        def _send_text(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == TOKEN_ROUTE:
                self._send_text(token_provider().encode("ascii"), "text/plain; charset=utf-8")
                return
            if self.path == RELOAD_ROUTE:
                self._send_text(
                    _RELOAD_JS.encode("utf-8"), "text/javascript; charset=utf-8"
                )
                return
            target = Path(self.translate_path(self.path))
            if target.is_dir():
                target = target / "index.html"
            if target.suffix == ".html" and target.is_file():
                body = target.read_bytes().replace(b"</body>", _INJECTION, 1)
                self._send_text(body, "text/html; charset=utf-8")
                return
            super().do_GET()

    return _Handler


def create_server(
    site_dir: Path, token_provider: Callable[[], str], port: int = 8321
) -> ThreadingHTTPServer:
    """Serveur prêt (non démarré) sur l'interface LOCALE uniquement (FR-012)."""
    handler = _make_handler(site_dir, token_provider)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise PortInUseError(port) from exc
        raise
    server.daemon_threads = True
    return server


def serve_in_thread(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread
