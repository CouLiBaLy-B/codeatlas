"""Service de prise de commande."""

from __future__ import annotations

from shopdemo.legacy.pricing import apply_legacy_discount
from shopdemo.models.order import Order
from shopdemo.services.catalog import CatalogService


class OrderService:
    """Crée des commandes en s'appuyant sur le catalogue (composition)."""

    def __init__(self) -> None:
        self.catalog = CatalogService(repo=_default_repo())
        self.history: list[Order] = []

    def place(self, customer: str, items: dict[str, int]) -> Order:
        """Crée une commande pour `customer` à partir de {nom_produit: quantité}."""
        order = Order(customer)
        for name, quantity in sorted(items.items()):
            product = self.catalog.repo.find(name)
            if product is not None:
                order.add(product, quantity)
        self.history.append(order)
        return order

    def total_after_discount(self, order: Order) -> float:
        return apply_legacy_discount(order.total())


def _default_repo():
    from shopdemo.storage.repo import InMemoryRepo

    return InMemoryRepo()
