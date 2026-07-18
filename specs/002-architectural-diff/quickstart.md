# Quickstart: valider le diff architectural

## Validation P1 — Baseline et diff

```bash
codeatlas baseline examples/python-demo                      # crée .codeatlas/baseline.json
codeatlas diff examples/python-demo                          # → « aucun changement », exit 0
# introduire un cycle + supprimer une API publique dans une copie du corpus, puis :
codeatlas diff <copie>                                       # → 1 cycle APPARU, 1 API DISPARUE
codeatlas diff <copie> > a.txt && codeatlas diff <copie> > b.txt && diff a.txt b.txt  # vide
```

## Validation P1 — Gate CI

```bash
codeatlas check <copie> --against-baseline --fail-on-new-cycles ; echo $?   # attendu : 3
codeatlas check <copie> --against-baseline ; echo $?                        # attendu : 0 (aucune règle)
rm .codeatlas/baseline.json && codeatlas check <copie> --against-baseline ; echo $?  # 0 + baseline créée
```

## Validation P2 — Commentaire de PR

```bash
codeatlas diff <copie> --format markdown | head -20
# attendu : marqueur <!-- codeatlas:arch-diff --> en 1re ligne, régressions en tête,
# détails traçables ; diff vide → « ✅ Aucun changement architectural »
```

## Validation P3 — Changelog

```bash
codeatlas baseline examples/python-demo --archive v1
# muter le corpus puis :
codeatlas baseline <copie> --archive v2
codeatlas build <copie> --out /tmp/atlas-chlog
# attendu : docs/changelog.md liste v1 → v2 avec les changements, page dans la nav
```

## Suite de tests

```bash
pytest tests/ -k "baseline or arch_delta or regression or diff_cli or gate or changelog"
ruff check . && mypy && pytest --cov=codeatlas --cov-fail-under=80 -m "not slow"
```
