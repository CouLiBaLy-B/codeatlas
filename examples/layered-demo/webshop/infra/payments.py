"""Encaissement Stripe (pattern adapter)."""

from __future__ import annotations

from webshop.domain.ports import PaymentPort


class StripeClient:
    """SDK Stripe factice."""

    def charge(self, cents: int) -> str:
        """Débite un montant en centimes."""
        return f"stripe:{cents}"


class StripeAdapter(PaymentPort):
    """Adapte `StripeClient` au contrat `PaymentPort` du domaine (pattern adapter)."""

    def __init__(self) -> None:
        self.client = StripeClient()

    def pay(self, amount: float) -> str:
        """Encaisse via Stripe."""
        return self.client.charge(int(amount * 100))
