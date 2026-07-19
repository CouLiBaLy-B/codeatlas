"""Modèle Produit."""

from __future__ import annotations

from dataclasses import dataclass

from mypkg.util import slugify


@dataclass
class Product:
    """Un produit du catalogue."""

    name: str
    price: float

    @property
    def slug(self) -> str:
        """Identifiant lisible dérivé du nom."""
        return slugify(self.name)
