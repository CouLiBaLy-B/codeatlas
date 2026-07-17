"""Ports du domaine (interfaces vers l'extérieur)."""

from __future__ import annotations

from typing import Protocol


class PaymentPort(Protocol):
    """Contrat d'encaissement."""

    def pay(self, amount: float) -> str:
        """Encaisse un montant et renvoie un reçu."""
        ...
