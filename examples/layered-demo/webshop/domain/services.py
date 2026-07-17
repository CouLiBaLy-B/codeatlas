"""Services applicatifs du domaine."""

from __future__ import annotations

from webshop.domain.events import EventBus
from webshop.domain.models import DiscountedPrice, Price
from webshop.infra.database import DatabaseConnection
from webshop.infra.payments import StripeAdapter


class PricingService:
    """Calcule les prix de vente."""

    def price_of(self, name: str) -> float:
        """Prix TTC du produit `name`."""
        base = Price(10.0)
        if name.startswith("promo"):
            return DiscountedPrice(base, 0.1).total()
        return base.total()


class CheckoutService:
    """Orchestre une commande de bout en bout."""

    def __init__(self) -> None:
        self.pricing = PricingService()
        self.bus = EventBus()
        self.db = DatabaseConnection.get_instance()
        self.payment = StripeAdapter()

    def order(self, name: str, quantity: int) -> str:
        """Commande `quantity` unités de `name` et renvoie le reçu."""
        amount = self.pricing.price_of(name) * quantity
        receipt = self.payment.pay(amount)
        self.bus.notify(f"order:{name}")
        self.db.save(name, quantity)
        return receipt
