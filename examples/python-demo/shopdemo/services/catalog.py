"""Service de catalogue : façade au-dessus du dépôt de produits."""

from __future__ import annotations

from shopdemo.models.product import DigitalProduct, Product
from shopdemo.storage.repo import InMemoryRepo


class CatalogService:
    """Expose le catalogue ; le dépôt est fourni par l'appelant (agrégation)."""

    def __init__(self, repo: InMemoryRepo) -> None:
        self.repo = repo

    def register(self, name: str, price: float, digital: bool = False) -> Product:
        """Crée et enregistre un produit, numérique ou physique."""
        product: Product
        if digital:
            product = DigitalProduct(name, price, download_url=f"https://dl.example/{name}")
        else:
            product = Product(name, price)
        self.repo.save(product)
        return product

    def price_of(self, name: str) -> float:
        """Prix TTC d'un produit du catalogue, 0.0 s'il est inconnu."""
        product = self.repo.find(name)
        if product is None:
            return 0.0
        return product.price_with_tax()
