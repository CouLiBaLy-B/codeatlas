"""Routes HTTP de la boutique."""

from __future__ import annotations

from fastapi import FastAPI

from webshop.domain.services import CheckoutService

app = FastAPI()
_checkout = CheckoutService()


@app.get("/price/{name}")
def get_price(name: str) -> float:
    """Prix TTC d'un produit."""
    return _checkout.pricing.price_of(name)


@app.post("/checkout")
def checkout(name: str, quantity: int) -> str:
    """Passe une commande."""
    return _checkout.order(name, quantity)
