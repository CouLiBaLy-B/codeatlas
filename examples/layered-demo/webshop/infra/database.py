"""Connexion base de données (pattern singleton) + contre-exemple."""

from __future__ import annotations


class DatabaseConnection:
    """Connexion unique partagée (pattern singleton)."""

    _instance: DatabaseConnection | None = None

    @classmethod
    def get_instance(cls) -> DatabaseConnection:
        """Renvoie l'instance unique, créée au premier appel."""
        if cls._instance is None:
            cls._instance = DatabaseConnection()
        return cls._instance

    def save(self, name: str, quantity: int) -> None:
        """Écrit une ligne de commande."""
        print("save", name, quantity)


class SingletonRegistry:
    """Contre-exemple : le nom évoque un singleton mais rien ne l'impose."""

    def register(self, key: str) -> None:
        """Enregistre une clé quelconque."""
        print(key)
