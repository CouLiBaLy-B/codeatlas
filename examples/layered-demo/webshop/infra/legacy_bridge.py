"""Pont hérité — importe la couche API depuis l'infra : violation volontaire."""

from __future__ import annotations

from webshop.api.routes import app


def route_count() -> int:
    """Nombre de routes exposées (à ne pas reproduire : infra → api)."""
    return len(getattr(app, "routes", []))
