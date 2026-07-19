"""Cœur applicatif : orchestre les modèles et les utilitaires (imports internes)."""

from __future__ import annotations

from mypkg.models.order import Order
from mypkg.models.product import Product
from mypkg.util import clamp


def build_order(names_and_prices: list[tuple[str, float]]) -> Order:
    """Construit une commande à partir de couples (nom, prix)."""
    products = [Product(name=name, price=price) for name, price in names_and_prices]
    return Order(products=products)


def discounted_total(order: Order, percent: int) -> float:
    """Applique une remise bornée entre 0 et 100 % au total d'une commande."""
    rate = clamp(percent, 0, 100) / 100
    return order.total() * (1 - rate)
