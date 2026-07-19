# Quickstart: Détection de la racine des sources — validation

**Feature**: 005-source-root-detection

Prérequis : `uv sync`, corpus d'exemple (dont le nouveau `examples/src-layout-demo/`).

## 1. Layout `src/` : les imports se résolvent (US1, SC-001/SC-002)

```bash
codeatlas export examples/src-layout-demo --format graph | \
  python -c "import sys,json; g=json.load(sys.stdin); \
  print('arêtes imports :', sum(1 for e in g['edges'] if e['kind']=='imports'))"
```

Attendu : nombre d'arêtes d'import > 0 ; les modules sont nommés `mypkg.*`
(sans segment `src`). Le diagramme de dépendances de packages n'est plus vide.

Validation grandeur nature sur CodeAtlas lui-même (layout `src/`) :

```bash
codeatlas build . --out /tmp/self --no-site
# la page Santé montre un couplage (fan-in/fan-out) non nul ;
# la page Architecture montre les dépendances réelles entre packages.
```

## 2. Non-régression sur un package à la racine (SC-003)

```bash
UPDATE_GOLDEN= codeatlas export examples/python-demo --format graph > /tmp/a.json
# python-demo : package `shopdemo` à la racine → noms et arêtes inchangés
```

Attendu : `pytest tests/golden` passe SANS régénération — aucun golden ne bouge.

## 3. Déterminisme (SC-004)

```bash
codeatlas export examples/src-layout-demo --format graph > /tmp/1.json
codeatlas export examples/src-layout-demo --format graph > /tmp/2.json
diff /tmp/1.json /tmp/2.json && echo OK
```

## 4. Répertoires générés ignorés (US3, SC-005)

```bash
codeatlas build examples/python-demo --out examples/python-demo-docs   # produit un site
codeatlas export examples/python-demo --format graph | \
  grep -c "python-demo-docs"   # attendu : 0 — le site généré n'est pas analysé
```

Attendu : aucun module ni sous-projet ne provient de `python-demo-docs/`
(marqueur `.codeatlas-generated` détecté). Nettoyer ensuite le dossier de test.

## 5. Suite de tests

```bash
uv run pytest                              # unit + golden + intégration, couverture ≥ 80 %
uv run pytest tests/unit/test_import_root.py   # détection de racine (cas src/, sous-répertoire, orphelin, repli)
```

## 6. Performance (SC-006)

```bash
time codeatlas build <repo-src-layout-50k> --out /tmp/perf   # < 30 s, pas de dégradation
```
