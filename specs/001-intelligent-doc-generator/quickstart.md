# Quickstart: valider CodeAtlas de bout en bout

Guide de validation — prouve que la feature fonctionne, story par story. Les détails
d'interface sont dans [contracts/](contracts/), le modèle dans
[data-model.md](data-model.md).

## Prérequis

```bash
# Python ≥ 3.11 + uv
cd codeatlas
uv venv && source .venv/bin/activate
uv pip install -e ".[site,dev]"          # cœur + site + outillage dev
# stories multi-langage : uv pip install -e ".[all,dev]"
```

## Validation P1 — Documenter un dépôt Python en une commande

```bash
codeatlas build examples/python-demo --out /tmp/atlas-demo
```

**Attendu** :

- exit code 0 ; résumé console : fichiers analysés, 1 fichier ignoré (le
  `invalid_syntax.py` volontaire du corpus), avertissements ;
- `/tmp/atlas-demo/site/` : site navigable hors-ligne (ouvrir `index.html` sans
  réseau — les diagrammes Mermaid se rendent) ;
- vue d'ensemble, diagrammes de classes par module, diagramme de dépendances de
  packages avec le cycle volontaire du corpus surligné, référence API complète,
  section « éléments non analysés » listant le fichier invalide et sa raison.

## Validation transverse — Déterminisme et hors-ligne

```bash
codeatlas build examples/python-demo --out /tmp/a
codeatlas build examples/python-demo --out /tmp/b
diff -r /tmp/a /tmp/b && echo "DÉTERMINISTE ✅"        # doit être vide (SC-002)

pytest tests/integration/test_no_network.py            # socket bloquée (SC-007)
```

## Validation P2 — Graphes d'appels

```bash
codeatlas build examples/python-demo --out /tmp/atlas-demo --depth 3
codeatlas diagram examples/python-demo --type calls --focus cli.main --depth 2
```

**Attendu** : section « Points d'entrée » (CLI et routes factices du corpus) ; le
diagramme focalisé contient les chaînes d'appel attendues, liens incertains en
pointillés avec légende.

## Validation P2 — Santé du code

**Attendu dans le site** : page « Santé » avec complexité/taille/couplage/couverture
doc par module (statuts ok/warn/critical) ; la fonction volontairement complexe du
corpus en `critical` ; la fonction jamais appelée dans « code probablement mort ».

## Validation P2 — Mode CI

```bash
codeatlas check examples/python-demo --min-doc-coverage 99 ; echo "exit=$?"   # attendu : 3
codeatlas check examples/python-demo --min-doc-coverage 10 ; echo "exit=$?"   # attendu : 0
# GitHub Action : voir action/ — job qui build + publie sur Pages à chaque push
```

## Validation P3 — Architecture & patterns

```bash
codeatlas build examples/layered-demo --out /tmp/atlas-layered
```

**Attendu** : vue « Architecture » — couches api/domain/infra détectées, la violation
volontaire (infra → api via `legacy_bridge`) signalée avec ses indices ; pages des
classes mentionnant singleton/factory/observer/adapter/decorator avec les indices de
détection, et aucun des contre-exemples du corpus détecté à tort.

## Validation P3 — Monorepo polyglotte

```bash
codeatlas build examples/monorepo-demo --out /tmp/atlas-mono
```

**Attendu** : les 3 sous-projets (front TS, back Python, service Java) détectés et
documentés dans un site unique ; graphe inter-services reflétant les dépendances
déclarées ; navigation croisée.

## Suite de tests complète

```bash
ruff check . && mypy src/
pytest --cov=codeatlas --cov-fail-under=80
```

**Attendu** : tout vert — la CI reproduit exactement ces commandes.
