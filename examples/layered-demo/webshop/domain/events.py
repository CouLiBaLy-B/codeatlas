"""Bus d'événements du domaine (pattern observer) + contre-exemple."""

from __future__ import annotations


class OrderObserver:
    """Réagit aux événements de commande."""

    def update(self, event: str) -> None:
        """Traite un événement."""
        print(event)


class EventBus:
    """Notifie les abonnés des événements du domaine (pattern observer)."""

    def __init__(self) -> None:
        self.observers: list[OrderObserver] = []

    def subscribe(self, observer: OrderObserver) -> None:
        """Abonne un observateur."""
        self.observers.append(observer)

    def notify(self, event: str) -> None:
        """Diffuse un événement à tous les abonnés."""
        for observer in self.observers:
            observer.update(event)


class Notifier:
    """Contre-exemple : `notify_user` sans abonnés ni diffusion — pas un observer."""

    def notify_user(self, message: str) -> str:
        """Formate un message pour un utilisateur unique."""
        return message.upper()
