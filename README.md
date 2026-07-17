# CodeAtlas

**Générateur de documentation intelligente par analyse statique** — pointez-le sur un
dépôt Python, TypeScript/JavaScript ou Java (monorepos compris) et obtenez un site de
documentation navigable, toujours à jour : diagrammes UML, graphes d'appels, détection
d'architecture et de design patterns, santé du code. **Déterministe, hors-ligne, sans
LLM.**

![CI](https://img.shields.io/badge/CI-ruff%20%7C%20mypy%20%7C%20pytest-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen)

## Une commande

```bash
pip install "codeatlas[site]"
codeatlas build ./mon-repo
# → ouvrir codeatlas-docs/site/index.html (consultable sans réseau)
```

## Ce que contient la documentation générée

| Vue | Contenu |
| --- | --- |
| **Vue d'ensemble** | statistiques, dépendances de packages, cycles surlignés en rouge |
| **Modules** | diagramme de classes UML + référence API extraite des docstrings/JSDoc/Javadoc |
| **Points d'entrée** | routes HTTP, commandes CLI, `main` — avec le graphe d'appels de chacun |
| **Architecture** | couches détectées, violations justifiées, design patterns (singleton, factory, observer, adapter, decorator) avec leurs indices |
| **Santé du code** | complexité, couplage, couverture de doc, code probablement mort avec confiance |
| **Monorepo** | sous-projets détectés par manifestes, graphe de dépendances inter-services |

Chaque affirmation est traçable : les liens d'appel incertains (réflexion, `getattr`)
sont **en pointillés**, jamais présentés comme sûrs ; chaque détection porte ses
indices.

## Garanties

- **Déterministe** : deux exécutions → sorties identiques octet pour octet (testé en CI).
- **Hors-ligne** : zéro appel réseau, mermaid.js vendorisé, site consultable en `file://`.
- **Tolérant** : un fichier invalide est signalé, jamais bloquant.
- **Sans exécution** : le code analysé n'est jamais importé ni exécuté.

## Commandes

```bash
codeatlas build PATH [--out DIR] [--no-site] [--include-private] [--json-report F]
codeatlas check PATH [--max-package-cycles N] [--min-doc-coverage PCT] \
                     [--max-critical-symbols N]        # mode CI : exit 3 si violation
codeatlas diagram PATH --type calls --focus cli.main --depth 2   # diagramme focalisé
```

Configuration optionnelle via `codeatlas.toml` ou `[tool.codeatlas]`
(voir [le contrat](specs/001-intelligent-doc-generator/contracts/config-schema.md)).

## Langages et extras

| Extra | Contenu |
| --- | --- |
| `codeatlas` | cœur + analyseur **Python** (ast natif) |
| `codeatlas[site]` | site MkDocs Material |
| `codeatlas[javascript]` | analyseur **JS/TS** (tree-sitter, wheels précompilées) |
| `codeatlas[java]` | analyseur **Java** (tree-sitter) |
| `codeatlas[all]` | tout |

## Intégration continue

Une GitHub Action est fournie ([action/](action/)) : régénère la documentation à
chaque push et fait échouer le job sur vos seuils qualité (nouveau cycle de packages,
chute de couverture de doc…). CodeAtlas se contrôle lui-même avec `codeatlas check .`.

## Corpus d'exemples

- [examples/python-demo](examples/python-demo) — héritages, cycle volontaire, code mort, fichier invalide
- [examples/layered-demo](examples/layered-demo) — couches api/domain/infra, violation volontaire, 5 patterns + contre-exemples
- [examples/ts-demo](examples/ts-demo) / [examples/java-demo](examples/java-demo) — corpus TS et Java
- [examples/monorepo-demo](examples/monorepo-demo) — front TS + back Python + service Java + module non supporté

## Développement

Projet piloté par [spec-kit](https://github.com/github/spec-kit) : constitution,
spécification, plan, contrats et tâches sont dans
[specs/001-intelligent-doc-generator/](specs/001-intelligent-doc-generator/).

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[all,site,dev]"
pytest --cov=codeatlas          # 201 tests, couverture ≥ 80 % exigée
ruff check . && mypy
codeatlas build . --out codeatlas-docs-self   # dogfooding
```

## Licence

MIT
