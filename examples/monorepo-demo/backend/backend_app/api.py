"""API des commandes."""

from __future__ import annotations


class OrdersApi:
    """Expose les commandes aux autres services."""

    def list_orders(self) -> list[str]:
        """Liste les identifiants de commandes."""
        return ["ord-1", "ord-2"]
