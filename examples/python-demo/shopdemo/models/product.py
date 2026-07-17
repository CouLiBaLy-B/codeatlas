"""Produits du catalogue."""

from __future__ import annotations


class Product:
    """Un produit physique du catalogue.

    Attributes:
        name: nom commercial affiché.
        price: prix unitaire hors taxes, en euros.
    """

    name: str
    price: float

    def __init__(self, name: str, price: float) -> None:
        self.name = name
        self.price = price

    def price_with_tax(self, rate: float = 0.2) -> float:
        """Prix TTC pour un taux de TVA donné."""
        return self.price * (1 + rate)

    def _rounded(self, value: float) -> float:
        return round(value, 2)


class DigitalProduct(Product):
    """Produit dématérialisé : livraison instantanée, TVA réduite."""

    download_url: str

    def __init__(self, name: str, price: float, download_url: str) -> None:
        super().__init__(name, price)
        self.download_url = download_url

    def price_with_tax(self, rate: float = 0.055) -> float:
        """La TVA réduite s'applique aux biens numériques."""
        return super().price_with_tax(rate)


class _ProductCache:
    def __init__(self) -> None:
        self.entries: dict[str, Product] = {}
