"""Routes d'API web factices (style FastAPI) — points d'entrée pour CodeAtlas."""

from __future__ import annotations

from fastapi import FastAPI

from shopdemo.services.catalog import CatalogService
from shopdemo.storage.repo import InMemoryRepo

app = FastAPI()
_catalog = CatalogService(InMemoryRepo())


@app.get("/products")
def list_products() -> list[str]:
    """Liste les noms de produits du catalogue."""
    return _catalog.repo.all_names()


@app.post("/products")
def create_product(name: str, price: float) -> float:
    """Crée un produit et renvoie son prix TTC."""
    _catalog.register(name, price)
    return _catalog.price_of(name)
