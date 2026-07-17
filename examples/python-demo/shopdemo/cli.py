"""Point d'entrée en ligne de commande de la boutique de démonstration."""

from __future__ import annotations

import click

from shopdemo.quality import tangled_pricing
from shopdemo.services.orders import OrderService


@click.command()
@click.option("--customer", default="demo", help="Nom du client de démonstration.")
def main(customer: str) -> None:
    """Passe une commande de démonstration et affiche son total."""
    service = OrderService()
    service.catalog.register("clavier", 49.9)
    service.catalog.register("ebook-python", 12.0, digital=True)
    order = service.place(customer, {"clavier": 1, "ebook-python": 2})
    total = service.total_after_discount(order)
    print(f"total: {tangled_pricing(total, 'eu', False, None):.2f}")


if __name__ == "__main__":
    main()
