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

## Entrées

| Entrée | Défaut | Description |
| --- | --- | --- |
| `path` | `.` | racine du dépôt à analyser |
| `out` | `codeatlas-docs` | répertoire de sortie |
| `config` | — | chemin d'un `codeatlas.toml` |
| `python-version` | `3.12` | version de Python |
| `check-args` | — | arguments de `codeatlas check` (vide = non bloquant) |
