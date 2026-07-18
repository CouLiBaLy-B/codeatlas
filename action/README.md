# GitHub Action CodeAtlas

Régénère la documentation à chaque push et publie le site en artefact (ou sur
GitHub Pages), avec des seuils qualité optionnels qui font échouer le job.

## Usage minimal

```yaml
name: docs
on:
  push:
    branches: [main]

jobs:
  codeatlas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: CouLiBaLy-B/codeatlas/action@main
        with:
          path: .
```

## Avec seuils qualité bloquants (mode `check`)

```yaml
      - uses: CouLiBaLy-B/codeatlas/action@main
        with:
          path: .
          check-args: "--max-package-cycles 0 --min-doc-coverage 60"
```

Le job échoue (exit 3) si un seuil est violé — par exemple si un nouveau cycle de
dépendances entre packages est introduit.

## Publication sur GitHub Pages

Ajoutez après l'action :

```yaml
      - uses: actions/upload-pages-artifact@v3
        with:
          path: codeatlas-docs/site
      - uses: actions/deploy-pages@v4
```

## Diff architectural en PR (feature 002)

```yaml
on:
  pull_request:

permissions:
  contents: read
  pull-requests: write   # requis pour pr-comment

jobs:
  codeatlas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: CouLiBaLy-B/codeatlas/action@main
        with:
          path: .
          baseline: default        # .codeatlas/baseline.json (committée)
          pr-comment: "true"
```

Chaque push de la PR met à jour **le même** commentaire (marqueur
`codeatlas:arch-diff`) : cycles/violations/APIs apparus ou disparus, régressions en
tête. Le gate échoue (exit 3) selon les règles `[check]` de `codeatlas.toml`
(`fail_on_new_cycles`, `fail_on_removed_public_api`…). Workflow type : la branche
principale rafraîchit la baseline (`codeatlas baseline . && git commit`), les PR
comparent.

## Entrées

| Entrée | Défaut | Description |
| --- | --- | --- |
| `path` | `.` | racine du dépôt à analyser |
| `out` | `codeatlas-docs` | répertoire de sortie |
| `config` | — | chemin d'un `codeatlas.toml` |
| `python-version` | `3.12` | version de Python |
| `check-args` | — | arguments de `codeatlas check` (vide = non bloquant) |
| `baseline` | — | `default` ou chemin : active diff + gate architectural |
| `pr-comment` | `false` | poste/met à jour le commentaire de PR |
