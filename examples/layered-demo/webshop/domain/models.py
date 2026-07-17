"""Modèle métier : prix simples et décorés."""

from __future__ import annotations


class Price:
    """Prix de base."""

    def __init__(self, amount: float) -> None:
        self.amount = amount

    def total(self) -> float:
        """Montant total."""
        return self.amount


class DiscountedPrice(Price):
    """Enveloppe un `Price` et applique une remise (pattern decorator)."""

    def __init__(self, inner: Price, rate: float) -> None:
        super().__init__(inner.total())
        self.inner = inner
        self.rate = rate

    def total(self) -> float:
        """Montant remisé."""
        return self.inner.total() * (1 - self.rate)
