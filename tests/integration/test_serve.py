"""T022 — Intégration du mode atelier (US3) : service local, reload, port occupé."""

from __future__ import annotations

import shutil
import socket
import urllib.request
from pathlib import Path

import pytest

from codeatlas import api
from codeatlas.cli import main
from codeatlas.serve.server import RELOAD_ROUTE, TOKEN_ROUTE, PortInUseError

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(CORPUS, target)
    return target


@pytest.fixture()
def session(workspace: Path, tmp_path: Path):
    live = api.serve_docs(workspace, port=0, watch=False, workdir=tmp_path / "atelier")
    yield live
    live.stop()


def _get(port: int, route: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{route}", timeout=5) as response:
        return response.status, response.read()


def test_serves_full_site_on_localhost(session) -> None:
    port = session.server.server_address[1]
    status, body = _get(port, "/")
    assert status == 200
    assert b"<html" in body.lower()
    status, body = _get(port, "/architecture.html")
    assert status == 200
    assert b"atlas-explorer" in body


def test_html_responses_embed_reload_script_without_touching_disk(session) -> None:
    port = session.server.server_address[1]
    _, body = _get(port, "/index.html")
    assert RELOAD_ROUTE.encode() in body  # injecté à la volée…
    on_disk = (session.site_dir / "index.html").read_bytes()
    assert RELOAD_ROUTE.encode() not in on_disk  # …jamais dans l'artefact (constitution I)
    status, script = _get(port, RELOAD_ROUTE)
    assert status == 200 and TOKEN_ROUTE.encode() in script


def test_token_changes_after_rebuild(session, workspace: Path) -> None:
    port = session.server.server_address[1]
    _, before = _get(port, TOKEN_ROUTE)
    target = workspace / "shopdemo" / "quality.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n\ndef reloaded() -> None:\n    pass\n",
        encoding="utf-8",
    )
    session.notify_change("shopdemo/quality.py")
    session.flush()
    _, after = _get(port, TOKEN_ROUTE)
    assert after != before
    _, page = _get(port, "/modules/shopdemo.quality.html")
    assert b"reloaded" in page


def test_occupied_port_raises_and_cli_exits_4(workspace: Path, tmp_path: Path, runner) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        with pytest.raises(PortInUseError):
            api.serve_docs(workspace, port=port, watch=False, workdir=tmp_path / "a")
        result = runner.invoke(
            main, ["serve", str(workspace), "--port", str(port), "--no-watch"]
        )
        assert result.exit_code == 4


def test_stop_frees_the_port(workspace: Path, tmp_path: Path) -> None:
    live = api.serve_docs(workspace, port=0, watch=False, workdir=tmp_path / "atelier")
    port = live.server.server_address[1]
    live.stop()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", port))  # doit réussir : arrêt propre
