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
pip install "codeatlas-doc[site]"
codeatlas build ./mon-repo
# → ouvrir codeatlas-docs/site/index.html (consultable sans réseau)
```

> Le nom de distribution est `codeatlas-doc` (« codeatlas » était pris sur PyPI) ;
> la commande et l'import restent `codeatlas`.

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

## Explorer la documentation

Le site généré n'est pas seulement lisible, il est **explorable** — toujours
hors-ligne, y compris ouvert en `file://` :

- **Explorateur d'architecture** (page Architecture) : le graphe de code en vue
  zoomable par niveaux (sous-projets → packages → modules), fiche au clic,
  filtres par langage/couche/sous-projet encodés dans l'URL (partageables).
  Sans JavaScript, les diagrammes statiques restent le repli.
- **Recherche de symboles** (touche `s` sur toute page) : modules, classes,
  fonctions et méthodes avec signatures — classement déterministe, jamais de
  résultat inventé.
- **Tableau de bord** (page Santé) : tables triables au clic, carte
  proportionnelle SVG cliquable (le module le plus préoccupant saute aux yeux),
  fichiers ignorés listés avec leur motif.
- **Fiches enrichies** : extrait de source exact de chaque symbole (repliable),
  appelants/appelés cliquables, liens incertains distingués. `[explorer]
  include_source = false` pour exclure les extraits.
- **Mode atelier** : `codeatlas serve PATH` sert la documentation sur
  `127.0.0.1` et la régénère à chaque sauvegarde (analyse incrémentale par
  sous-projet, rechargement automatique du navigateur). Un fichier cassé ne tue
  jamais la session : il est signalé et le reste du site continue d'être servi.

`--no-explorer` (ou `[explorer] enabled = false`) restitue le site strictement
statique. Les vues interactives sont vendorisées (Cytoscape.js, empreinte
SHA-256 vérifiée par test) : **aucun CDN, aucune requête externe**.

## Garanties

- **Déterministe** : deux exécutions → sorties identiques octet pour octet (testé en CI).
- **Hors-ligne** : zéro appel réseau, mermaid.js vendorisé, site consultable en `file://`.
- **Tolérant** : un fichier invalide est signalé, jamais bloquant.
- **Sans exécution** : le code analysé n'est jamais importé ni exécuté.

## Commandes

```bash
codeatlas build PATH [--out DIR] [--no-site] [--no-explorer] [--include-private]
codeatlas serve PATH [--port 8321] [--open] [--no-watch] [--json]   # mode atelier
codeatlas check PATH [--max-package-cycles N] [--min-doc-coverage PCT] \
                     [--max-critical-symbols N]        # mode CI : exit 3 si violation
codeatlas diagram PATH --type calls --focus cli.main --depth 2   # diagramme focalisé
```

Configuration optionnelle via `codeatlas.toml` ou `[tool.codeatlas]`
(voir [le contrat](specs/001-intelligent-doc-generator/contracts/config-schema.md)).

## Langages et extras

| Extra | Contenu |
| --- | --- |
| `codeatlas-doc` | cœur + analyseur **Python** (ast natif) |
| `codeatlas-doc[site]` | site MkDocs Material |
| `codeatlas-doc[javascript]` | analyseur **JS/TS** (tree-sitter, wheels précompilées) |
| `codeatlas-doc[java]` | analyseur **Java** (tree-sitter) |
| `codeatlas-doc[all]` | tout |

## L'architecture sous contrôle de version

Les sorties de CodeAtlas étant déterministes, **deux états du dépôt sont diffables** :

```bash
codeatlas baseline .                     # capture .codeatlas/baseline.json (committez-le)
codeatlas diff .                         # qu'est-ce que ma branche change à l'architecture ?
codeatlas check . --against-baseline \
  --fail-on-new-cycles --fail-on-removed-public-api    # gate CI : exit 3 sur régression
```

Le diff liste ce qui est **apparu/disparu** — cycles, violations de couches, APIs
publiques (signatures comprises), liens d'appel incertains, code mort — et l'Action
peut le poster en **commentaire de PR** mis à jour à chaque push. Les baselines
archivées (`codeatlas baseline --archive v1.2`) alimentent une page « Changelog
architectural » du site.

## Le substrat pour vos outils IA — sans IA

CodeAtlas n'appelle jamais de LLM, mais il produit le contexte fiable dont vos
assistants ont besoin — **sans que votre code ne quitte la machine** :

```bash
codeatlas export . --out .codeatlas/repomap.md   # carte compacte à budget, committable
codeatlas impact . --focus InMemoryRepo.find     # « qu'est-ce que ça touche ? »
codeatlas mcp .                                  # serveur MCP local (extra [mcp])
```

Configuration type pour Claude Code (`.mcp.json`) :

```json
{ "mcpServers": { "codeatlas": { "command": "codeatlas", "args": ["mcp", "."] } } }
```

Outils exposés : `overview`, `search_symbol`, `module_api`, `callers`/`callees`
(certitude distinguée), `impact`, `dead_code`, `reload`. Chaque réponse vient du
graphe — jamais d'invention.

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
