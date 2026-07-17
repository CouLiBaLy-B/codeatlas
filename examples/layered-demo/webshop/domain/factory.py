"""Fabrique d'observateurs (pattern factory) + contre-exemple."""

from __future__ import annotations

from webshop.domain.events import OrderObserver


class EmailObserver(OrderObserver):
    """Observateur e-mail."""

    def update(self, event: str) -> None:
        """Envoie un e-mail."""
        print("mail", event)


class SmsObserver(OrderObserver):
    """Observateur SMS."""

    def update(self, event: str) -> None:
        """Envoie un SMS."""
        print("sms", event)


class ObserverFactory:
    """Crée l'observateur adapté au canal demandé (pattern factory)."""

    def create(self, channel: str) -> OrderObserver:
        """Instancie l'observateur du canal."""
        if channel == "sms":
            return SmsObserver()
        return EmailObserver()


class ReportBuilder:
    """Contre-exemple : `create_report` ne fabrique aucun objet métier."""

    def create_report(self, rows: int) -> int:
        """Additionne des lignes — malgré son nom, pas une fabrique."""
        return rows * 2
