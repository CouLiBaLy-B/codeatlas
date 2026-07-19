"""Modèle Commande, dépend de Produit (import interne au package)."""

from __future__ import annotations

from dataclasses import dataclass, field

from mypkg.models.product import Product


@dataclass
class Order:
    """Une commande : une liste de produits."""

    products: list[Product] = field(default_factory=list)

    def total(self) -> float:
        """Somme des prix des produits."""
        return sum(p.price for p in self.products)
