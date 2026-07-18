"""T013 — Smoke test du serveur MCP (skip si l'extra n'est pas installé)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from codeatlas.bridge.server import build_server, mcp_available
from codeatlas.config import Config

CORPUS = Path(__file__).parents[2] / "examples" / "python-demo"

EXPECTED_TOOLS = {
    "overview",
    "search_symbol",
    "module_api",
    "callers",
    "callees",
    "impact",
    "dead_code",
    "reload",
}


def test_mcp_extra_detected() -> None:
    assert mcp_available()


def test_server_exposes_expected_tools() -> None:
    server = build_server(CORPUS, Config())
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == EXPECTED_TOOLS


def test_tools_carry_descriptions_for_discovery() -> None:
    server = build_server(CORPUS, Config())
    tools = asyncio.run(server.list_tools())
    for tool in tools:
        assert tool.description, f"outil sans description : {tool.name}"
