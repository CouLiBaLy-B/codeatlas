# Carte du dépôt : python-demo

> Carte déterministe générée par CodeAtlas (analyse statique, sans LLM) —
> destinée à servir de contexte fiable aux assistants IA.

## Vue d'ensemble
- Sous-projets : main (python)
- Modules : 15 · Symboles : 67 · Couverture doc : 81 %
- Couches : domain : shopdemo.models, shopdemo.services · infra : shopdemo.storage
- Fichiers non analysés : 1

## Points d'entrée
- shopdemo.cli.main (click) — `shopdemo.cli.main`
- python -m shopdemo.cli (python) — `shopdemo.cli`
- POST /products (web) — `shopdemo.webapp.create_product`
- GET /products (web) — `shopdemo.webapp.list_products`

## Parcours de lecture
1. shopdemo.cli (point d'entrée)
2. shopdemo.webapp (point d'entrée)
3. shopdemo.models.order (couche domain)
4. shopdemo.models.product (couche domain)
5. shopdemo.services.catalog (couche domain)
6. shopdemo.services.orders (couche domain)
7. shopdemo.storage.repo (couche infra)
8. shopdemo (autres)
9. shopdemo.broken (autres)
10. shopdemo.legacy (autres)
11. shopdemo.legacy.pricing (autres)
12. shopdemo.models (autres)
13. shopdemo.quality (autres)
14. shopdemo.services (autres)
15. shopdemo.storage (autres)

## API publique

### shopdemo
shopdemo : boutique factice servant de corpus de test à CodeAtlas.

### shopdemo.cli
Point d'entrée en ligne de commande de la boutique de démonstration.
- `main(customer: str) -> None` — Passe une commande de démonstration et affiche son total.

### shopdemo.webapp
Routes d'API web factices (style FastAPI) — points d'entrée pour CodeAtlas.
- `create_product(name: str, price: float) -> float` — Crée un produit et renvoie son prix TTC.
- `list_products() -> list[str]` — Liste les noms de produits du catalogue.

### shopdemo.models.product
Produits du catalogue.
- **DigitalProduct** — Produit dématérialisé : livraison instantanée, TVA réduite.
  - `__init__(name: str, price: float, download_url: str) -> None`
  - `price_with_tax(rate: float = 0.055) -> float` — La TVA réduite s'applique aux biens numériques.
- **Product** — Un produit physique du catalogue.
  - `__init__(name: str, price: float) -> None`
  - `price_with_tax(rate: float = 0.2) -> float` — Prix TTC pour un taux de TVA donné.

### shopdemo.services.catalog
Service de catalogue : façade au-dessus du dépôt de produits.
- **CatalogService** — Expose le catalogue ; le dépôt est fourni par l'appelant (agrégation).
  - `__init__(repo: InMemoryRepo) -> None`
  - `price_of(name: str) -> float` — Prix TTC d'un produit du catalogue, 0.0 s'il est inconnu.
  - `register(name: str, price: float, digital: bool = False) -> Product` — Crée et enregistre un produit, numérique ou physique.

### shopdemo.storage.repo
Dépôt de produits en mémoire.
- **InMemoryRepo** — Stocke les produits dans un dictionnaire — suffisant pour la démo.
  - `__init__() -> None`
  - `all_names() -> list[str]`
  - `find(name: str) -> Product | None`
  - `save(product: Product) -> None` — Enregistre ou remplace un produit.

### shopdemo.legacy.pricing
Règles de remise héritées. Importe services → cycle services ↔ legacy (voulu).
- `apply_legacy_discount(total: float) -> float` — Remise historique : 5 % au-delà de 100 €.
- `audit_catalog(service: CatalogService) -> int`
- `refresh_catalog_price(service: CatalogService) -> float` — Relit un prix via un appel dynamique — lien incertain pour l'analyse.

### shopdemo.models.order
Commandes et lignes de commande.
- **Order** — Une commande client, composée de lignes créées par la commande elle-même.
  - `__init__(customer: str) -> None`
  - `add(product: Product, quantity: int) -> None` — Ajoute une ligne à la commande.
  - `total() -> float` — Total TTC de la commande.
- **OrderLine** — Une ligne de commande : un produit et une quantité.
  - `__init__(product: Product, quantity: int) -> None`
  - `subtotal() -> float` — Sous-total TTC de la ligne.

### shopdemo.quality
Fonctions volontairement problématiques pour le tableau de bord santé.
- `forgotten_public_api() -> None`
- `tangled_pricing(total: float, region: str, vip: bool, coupon: str | None) -> float` — Tarification volontairement illisible (complexité cyclomatique > 20).

### shopdemo.services.orders
Service de prise de commande.
- **OrderService** — Crée des commandes en s'appuyant sur le catalogue (composition).
  - `__init__() -> None`
  - `place(customer: str, items: dict[str, int]) -> Order` — Crée une commande pour `customer` à partir de {nom_produit: quantité}.
  - `total_after_discount(order: Order) -> float`

### shopdemo.broken
Package contenant un fichier invalide — teste la tolérance (constitution IV).

### shopdemo.legacy
Code hérité — crée volontairement un cycle de packages avec services.

### shopdemo.models
Modèles métier de la boutique.

### shopdemo.services
Services applicatifs de la boutique.

### shopdemo.storage
Couche de persistance en mémoire.
