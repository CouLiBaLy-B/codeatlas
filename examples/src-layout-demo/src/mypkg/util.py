"""Utilitaires de bas niveau, sans dépendance interne."""

from __future__ import annotations


def slugify(text: str) -> str:
    """Réduit une chaîne à un identifiant simple."""
    return "-".join(text.lower().split())


def clamp(value: int, low: int, high: int) -> int:
    """Borne une valeur dans l'intervalle [low, high]."""
    return max(low, min(value, high))
