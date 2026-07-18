"""T003 — Émetteur canonique des données de vues (contrat explorer.md §3, R3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codeatlas.explorer.emit import SCHEMA_VERSION, ExplorerData, canonical_json, write_data


def test_canonical_json_sorts_keys_and_uses_fixed_separators() -> None:
    rendered = canonical_json({"b": 1, "a": [2, 1], "é": "accentué"})
    assert rendered == '{"a": [2, 1], "b": 1, "é": "accentué"}'  # UTF-8, jamais \\uXXXX


def test_canonical_json_rejects_non_deterministic_types() -> None:
    with pytest.raises(TypeError):
        canonical_json({"bad": {1, 2}})


def test_write_emits_one_js_file_per_view(tmp_path: Path) -> None:
    data = ExplorerData(
        graph={"levels": [], "nodes": [], "edges": []},
        search=[{"name": "x"}],
        dashboard={"rows": []},
    )
    written = write_data(data, tmp_path)
    expected = [
        tmp_path / "assets" / "data" / "atlas-dashboard.js",
        tmp_path / "assets" / "data" / "atlas-graph.js",
        tmp_path / "assets" / "data" / "atlas-search.js",
    ]
    assert written == expected  # chemins retournés triés
    text = (tmp_path / "assets" / "data" / "atlas-graph.js").read_text(encoding="utf-8")
    assert text.startswith("window.__ATLAS__ = window.__ATLAS__ || {};\n")
    assert text.endswith("\n") and not text.endswith("\n\n")  # LF final unique
    payload_line = text.splitlines()[1]
    assert payload_line.startswith('window.__ATLAS__["graph"] = ')
    payload = json.loads(payload_line.removeprefix('window.__ATLAS__["graph"] = ').rstrip(";"))
    assert payload["schema_version"] == SCHEMA_VERSION  # versionné pour le JS embarqué


def test_search_payload_wraps_entries_with_schema_version(tmp_path: Path) -> None:
    data = ExplorerData(graph={}, search=[{"name": "a"}], dashboard={})
    write_data(data, tmp_path)
    text = (tmp_path / "assets" / "data" / "atlas-search.js").read_text(encoding="utf-8")
    payload = json.loads(text.splitlines()[1].split(" = ", 1)[1].rstrip(";"))
    assert payload == {"entries": [{"name": "a"}], "schema_version": SCHEMA_VERSION}


def test_write_is_byte_for_byte_deterministic(tmp_path: Path) -> None:
    data = ExplorerData(
        graph={"nodes": [{"id": "b"}, {"id": "a"}]}, search=[], dashboard={"rows": []}
    )
    write_data(data, tmp_path / "one")
    write_data(data, tmp_path / "two")
    for name in ("atlas-graph.js", "atlas-search.js", "atlas-dashboard.js"):
        first = (tmp_path / "one" / "assets" / "data" / name).read_bytes()
        second = (tmp_path / "two" / "assets" / "data" / name).read_bytes()
        assert first == second
