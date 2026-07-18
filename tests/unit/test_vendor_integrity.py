"""T002 — Intégrité du JS vendorisé : version épinglée, empreinte vérifiée (R1)."""

from __future__ import annotations

import hashlib
from pathlib import Path

ASSETS = Path(__file__).parents[2] / "src" / "codeatlas" / "site" / "assets"

# Cytoscape.js 3.30.4 — toute mise à jour du vendor DOIT mettre à jour cette empreinte
# (et être relue : c'est le seul code tiers exécuté dans le site généré avec Mermaid).
CYTOSCAPE_SHA256 = "1bb5340e549511e111b31e5684872c949ad33d40ea5dba0ad8e7d90c62c7b3b9"


def test_cytoscape_vendored_and_pinned() -> None:
    vendored = ASSETS / "cytoscape.min.js"
    assert vendored.is_file(), "cytoscape.min.js doit être vendorisé (aucun CDN)"
    digest = hashlib.sha256(vendored.read_bytes()).hexdigest()
    assert digest == CYTOSCAPE_SHA256, "vendor modifié sans mise à jour de l'empreinte"


def test_no_remote_url_in_our_js_assets() -> None:
    """Les scripts maison n'embarquent aucune URL réseau (constitution I)."""
    for script in sorted(ASSETS.glob("atlas-*.js")):
        text = script.read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, script.name


def test_tables_script_wires_sort_and_filter() -> None:
    """FR-013 : le script des tables branche le tri ET le filtrage (tripwire)."""
    text = (ASSETS / "atlas-tables.js").read_text(encoding="utf-8")
    assert "data-atlas-sort" in text
    assert "data-atlas-filter" in text
    assert 'input.type = "search"' in text
