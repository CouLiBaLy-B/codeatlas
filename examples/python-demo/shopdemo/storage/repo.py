"""Dépôt de produits en mémoire."""

from __future__ import annotations

from shopdemo.models.product import Product


class InMemoryRepo:
    """Stocke les produits dans un dictionnaire — suffisant pour la démo."""

    def __init__(self) -> None:
        self.items: dict[str, Product] = {}

    def save(self, product: Product) -> None:
        """Enregistre ou remplace un produit."""
        self.items[product.name] = product

    def find(self, name: str) -> Product | None:
        return self.items.get(name)

    def all_names(self) -> list[str]:
        return sorted(self.items)
