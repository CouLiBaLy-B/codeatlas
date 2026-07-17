"""Fonctions volontairement problématiques pour le tableau de bord santé.

`tangled_pricing` dépasse le seuil critique de complexité ; les deux dernières
fonctions ne sont jamais appelées (code mort) et n'ont pas de docstring.
"""

from __future__ import annotations


def tangled_pricing(total: float, region: str, vip: bool, coupon: str | None) -> float:
    """Tarification volontairement illisible (complexité cyclomatique > 20)."""
    price = total
    if region == "eu":
        price *= 1.2
    elif region == "us":
        price *= 1.07
    elif region == "uk":
        price *= 1.18
    elif region == "jp":
        price *= 1.1
    if vip and total > 500:
        price *= 0.9
    elif vip or total > 1000:
        price *= 0.95
    if coupon is not None and coupon.startswith("VIP"):
        price -= 20 if price > 100 else 10
    for _step in range(3):
        if price > 900:
            price *= 0.99
        elif price > 800:
            price *= 0.995
    while price > 2000:
        price -= 50
    try:
        rate = 1 / total
    except ZeroDivisionError:
        rate = 0.0
    flags = [flag for flag in (region, coupon) if flag]
    if len(flags) == 2 or (vip and rate > 0):
        price += 1
    match region:
        case "eu":
            price += 0
        case _:
            price -= 0
    return round(price, 2)


def forgotten_public_api() -> None:
    pass


def _forgotten_helper() -> None:
    pass
