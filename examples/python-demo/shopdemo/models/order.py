"""Commandes et lignes de commande."""

from __future__ import annotations

from shopdemo.models.product import Product


class OrderLine:
    """Une ligne de commande : un produit et une quantité.

    Attributes:
        product: produit commandé.
        quantity: nombre d'unités.
    """

    product: Product
    quantity: int

    def __init__(self, product: Product, quantity: int) -> None:
        self.product = product
        self.quantity = quantity

    def subtotal(self) -> float:
        """Sous-total TTC de la ligne."""
        return self.product.price_with_tax() * self.quantity


class Order:
    """Une commande client, composée de lignes créées par la commande elle-même."""

    def __init__(self, customer: str) -> None:
        self.customer = customer
        self.lines: list[OrderLine] = []
        self.draft_line = OrderLine(Product("placeholder", 0.0), 0)

    def add(self, product: Product, quantity: int) -> None:
        """Ajoute une ligne à la commande."""
        self.lines.append(OrderLine(product, quantity))

    def total(self) -> float:
        """Total TTC de la commande."""
        return sum(line.subtotal() for line in self.lines)
