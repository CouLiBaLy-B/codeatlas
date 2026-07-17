# CodeAtlas

Générateur de documentation intelligente par **analyse statique** : diagrammes UML,
dépendances de packages avec cycles, graphes d'appels, métriques de santé et site
MkDocs Material — déterministe, hors-ligne, sans LLM.

> Projet en cours de développement, piloté par [spec-kit](https://github.com/github/spec-kit).
> Voir `specs/001-intelligent-doc-generator/` pour la spécification, le plan et les tâches.

## Installation (développement)

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[site,dev]"
```

## Usage

```bash
codeatlas build ./mon-repo          # génère le site de documentation
```

## Licence

MIT
