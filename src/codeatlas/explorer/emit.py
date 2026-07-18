"""Émission canonique des données de vues vers le site (contrat explorer.md §3).

Les données sont livrées en fichiers JS (`window.__ATLAS__`), jamais chargées par
`fetch()` : le site reste fonctionnel ouvert en `file://` (R3). JSON canonique :
clés triées, séparateurs fixes, UTF-8 brut, LF final unique — deux générations du
même graphe produisent des octets identiques (constitution I).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

_HEADER = "window.__ATLAS__ = window.__ATLAS__ || {};\n"


def canonical_json(payload: Any) -> str:
    """JSON déterministe ; refuse tout type non sérialisable (jamais de str() implicite)."""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(", ", ": "), allow_nan=False
    )


@dataclass(slots=True)
class ExplorerData:
    """Données des vues interactives, prêtes à émettre. Construites depuis l'IR only."""

    graph: dict[str, Any] = field(default_factory=dict)
    search: list[dict[str, Any]] = field(default_factory=list)
    dashboard: dict[str, Any] = field(default_factory=dict)


def _payload_js(key: str, payload: dict[str, Any]) -> str:
    versioned = {**payload, "schema_version": SCHEMA_VERSION}
    return f'{_HEADER}window.__ATLAS__["{key}"] = {canonical_json(versioned)};\n'


def write_data(data: ExplorerData, docs_dir: Path) -> list[Path]:
    """Écrit `assets/data/atlas-*.js` sous `docs_dir` → chemins écrits, triés."""
    target = docs_dir / "assets" / "data"
    target.mkdir(parents=True, exist_ok=True)
    contents = {
        "atlas-graph.js": _payload_js("graph", data.graph),
        "atlas-search.js": _payload_js("search", {"entries": data.search}),
        "atlas-dashboard.js": _payload_js("dashboard", data.dashboard),
    }
    written = []
    for name in sorted(contents):
        path = target / name
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(contents[name])
        written.append(path)
    return written
