"""Règles de remise héritées. Importe services → cycle services ↔ legacy (voulu)."""

from __future__ import annotations

from shopdemo.services.catalog import CatalogService


def apply_legacy_discount(total: float) -> float:
    """Remise historique : 5 % au-delà de 100 €."""
    if total > 100.0:
        return total * 0.95
    return total


def audit_catalog(service: CatalogService) -> int:
    return len(service.repo.all_names())


def refresh_catalog_price(service: CatalogService) -> float:
    """Relit un prix via un appel dynamique — lien incertain pour l'analyse."""
    handler = getattr(service, "price_of")
    return float(handler("clavier"))
