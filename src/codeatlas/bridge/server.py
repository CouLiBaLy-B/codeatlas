"""Serveur MCP local (stdio) — habillage FastMCP des outils purs de `tools.py`.

Extra requis : `codeatlas-doc[mcp]`. Transport stdio uniquement : aucune socket
réseau (FR-005). Les réponses proviennent exclusivement du graphe de code.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from codeatlas.config import Config

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP


def mcp_available() -> bool:
    from importlib.util import find_spec

    try:
        return find_spec("mcp") is not None
    except (ImportError, ValueError):  # pragma: no cover
        return False


def build_server(path: Path, config: Config) -> FastMCP:
    """Analyse le dépôt puis construit le serveur et ses outils."""
    from datetime import UTC, datetime

    from mcp.server.fastmcp import FastMCP

    from codeatlas import api
    from codeatlas.bridge import tools

    def _now() -> str:
        return datetime.now(tz=UTC).isoformat(timespec="seconds")

    # horodatage de CHARGEMENT (réponse runtime du serveur, jamais un artefact —
    # le déterminisme constitutionnel ne concerne que les sorties générées)
    state: dict[str, Any] = {"graph": api.analyze(path, config), "analyzed_at": _now()}

    server = FastMCP(
        "codeatlas",
        instructions=(
            "Graphe de code CodeAtlas : réponses issues d'une analyse statique "
            "déterministe et locale du dépôt — aucune invention, liens incertains "
            "explicitement marqués."
        ),
    )

    @server.tool()
    def overview() -> dict[str, Any]:
        """Vue d'ensemble du dépôt : sous-projets, couches, points d'entrée, métriques."""
        return {
            **tools.overview(state["graph"], config),
            "analyzed_at": state["analyzed_at"],
            "freshness_note": (
                "réponses issues de l'analyse chargée — utilisez `reload` "
                "après une modification du code"
            ),
        }

    @server.tool()
    def search_symbol(query: str) -> dict[str, Any]:
        """Cherche un symbole par nom (exact, suffixe, sous-chaîne) — résultats bornés."""
        return tools.search_symbol(state["graph"], query)

    @server.tool()
    def module_api(module: str) -> dict[str, Any]:
        """API publique d'un module : classes, méthodes, fonctions, signatures, docs."""
        return tools.module_api(state["graph"], module)

    @server.tool()
    def callers(symbol: str, depth: int = 1) -> dict[str, Any]:
        """Qui appelle ce symbole, jusqu'à `depth` niveaux (certitude distinguée)."""
        return tools.callers(state["graph"], symbol, depth)

    @server.tool()
    def callees(symbol: str, depth: int = 1) -> dict[str, Any]:
        """Ce que ce symbole appelle, jusqu'à `depth` niveaux (certitude distinguée)."""
        return tools.callees(state["graph"], symbol, depth)

    @server.tool()
    def impact(target: str, depth: int = 3) -> dict[str, Any]:
        """Analyse d'impact : appelants/importeurs par niveaux, points d'entrée atteints."""
        return tools.impact(state["graph"], target, depth)

    @server.tool()
    def dead_code() -> dict[str, Any]:
        """Code probablement mort, avec niveau de confiance et raison."""
        return tools.dead_code(state["graph"])

    @server.tool()
    def reload() -> dict[str, Any]:
        """Ré-analyse le dépôt (à utiliser après une modification du code)."""
        state["graph"] = api.analyze(path, config)
        state["analyzed_at"] = _now()
        return {
            "modules": tools.overview(state["graph"], config)["modules"],
            "symbols": len(state["graph"].nodes),
            "analyzed_at": state["analyzed_at"],
        }

    return server


def run(path: Path, config: Config) -> None:  # pragma: no cover — boucle stdio
    build_server(path, config).run()
