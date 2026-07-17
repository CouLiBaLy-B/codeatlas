"""Point d'entrée en ligne de commande de la boutique de démonstration."""

from __future__ import annotations

import sys

from shopdemo.services.orders import OrderService


def main(argv: list[str] | None = None) -> int:
    """Passe une commande de démonstration et affiche son total."""
    args = argv if argv is not None else sys.argv[1:]
    service = OrderService()
    service.catalog.register("clavier", 49.9)
    service.catalog.register("ebook-python", 12.0, digital=True)
    order = service.place("demo", {"clavier": 1, "ebook-python": 2})
    print(f"total: {service.total_after_discount(order):.2f} ({len(args)} args)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
