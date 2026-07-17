# Implementation Plan: CodeAtlas — Générateur de documentation intelligente

**Branch**: `001-intelligent-doc-generator` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-intelligent-doc-generator/spec.md`

## Summary

CodeAtlas analyse statiquement un dépôt (Python, puis JS/TS, puis Java — monorepos
compris) et génère un site MkDocs Material : diagrammes UML et dépendances avec cycles,
graphes d'appels depuis les points d'entrée, tableau de bord santé, vues architecture/
patterns et vue monorepo unifiée. Approche technique : chaque analyseur de langage
(ast natif pour Python — adapté de gendoc ; tree-sitter pour JS/TS/Java) produit un
fragment d'une **IR unique (graphe de code)** ; tout l'aval (diagrammes Mermaid,
métriques, détections, site, rapports) ne consomme que l'IR. Livraison par user
stories indépendantes : P1 = socle Python complet de bout en bout.

## Technical Context

**Language/Version**: Python ≥ 3.11 (tomllib natif, syntaxe `ast` récente)

**Primary Dependencies**: cœur : `click`, `rich`, `jinja2`, `networkx` ; extras :
`mkdocs-material` (`[site]`), `tree-sitter` + `tree-sitter-javascript` +
`tree-sitter-typescript` (`[javascript]`), `tree-sitter-java` (`[java]`),
`cairosvg` (`[svg]`), méta-extra `[all]`. mermaid.min.js vendorisé dans le package.

**Storage**: fichiers uniquement (sources en entrée, site + artefacts .md/.mmd/.svg/
.json en sortie). Aucune base, aucun état persistant.

**Testing**: pytest + pytest-cov (couverture ≥ 80 % imposée en CI), golden files
versionnés pour tous les rendus, test de double exécution (diff binaire vide), test
zéro-réseau (socket bloquée), corpus d'exemples par langage dans `examples/`.
Lint/typage : ruff + mypy strict.

**Target Platform**: CLI multiplateforme (Linux, macOS, Windows) ; CI GitHub Actions.

**Project Type**: bibliothèque Python + CLI en façade (constitution II).

**Performance Goals**: dépôt de 50 000 lignes analysé et site généré en < 30 s sur
machine de développement standard (SC-001) ; parsing ≥ ~10 000 lignes/s.

**Constraints**: sortie déterministe octet pour octet (SC-002) ; zéro appel réseau à
l'exécution (SC-007) ; tolérance aux fichiers non parsables (FR-004) ; aucun
compilateur/runtime externe requis (grammaires en wheels précompilées) ; hors-ligne
complet, y compris la consultation du site (mermaid.js vendorisé).

**Scale/Scope**: cible nominale ~50k lignes, dégradation au pire linéaire jusqu'à
~500k lignes ; 3 langages ; 6 user stories dont P1 = MVP autonome.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principe | Évaluation | Verdict |
| --- | --- | --- | --- |
| I | Analyse statique déterministe | Aucun LLM/réseau ; conventions de tri imposées ; interdiction horodatages/aléa dans les artefacts ; tests double-run + zéro-réseau en CI (R10) | ✅ |
| II | Bibliothèque d'abord, CLI en façade | API publique `codeatlas.api` ; `cli.py` = fine couche Click ; sorties JSON pour la CI (R9) | ✅ |
| III | IR unifiée multi-langage | Analyseurs → fragments d'IR via contrat unique ; diagrammes/métriques/détections/site ne consomment que l'IR ; mkdocstrings écarté pour cette raison (R3) | ✅ |
| IV | Tolérance aux défaillances | Fichier non parsable → avertissement structuré + section « éléments non analysés » ; échec bloquant uniquement si 0 fichier analysable | ✅ |
| V | Test-first et qualité mesurée | TDD par story ; couverture ≥ 80 % ; corpus d'exemples réalistes ; golden files (R10) | ✅ |

**Contraintes techniques de la constitution** : Python ≥ 3.11 ✅ ; parseurs embarqués
sans runtime externe ✅ (wheels tree-sitter) ; MkDocs Material + Mermaid ✅ ; PyPI +
GitHub Action ✅ ; < 30 s / 50k lignes ✅ (objectif de perf) ; hors-ligne/MIT ✅.

**Re-check post-Phase 1** : ✅ — le design (data-model, contrats) n'introduit aucune
violation ; pas d'entrée en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-intelligent-doc-generator/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques argumentées
├── data-model.md        # Phase 1 — modèle de l'IR et des entités
├── quickstart.md        # Phase 1 — guide de validation de bout en bout
├── contracts/           # Phase 1 — contrats d'interface
│   ├── cli.md           # Commandes, options, exit codes, rapport JSON
│   ├── ir-schema.md     # Schéma du graphe de code (nœuds, arêtes, certitude)
│   ├── analyzer-protocol.md  # Contrat des analyseurs et des insights
│   └── config-schema.md # Schéma codeatlas.toml / [tool.codeatlas]
└── tasks.md             # Phase 2 (/speckit-tasks — pas encore créé)
```

### Source Code (repository root)

```text
src/codeatlas/
├── ir/                  # Modèle du graphe de code : nœuds, arêtes, certitude,
│                        #   export JSON canonique (AUCUNE dépendance langage)
├── analyzers/
│   ├── base.py          # Contrat LanguageAnalyzer + registre + découverte fichiers
│   ├── python/          # ast natif — adapté de gendoc (P1)
│   ├── javascript/      # tree-sitter JS/TS (P3, story 6)
│   └── java/            # tree-sitter Java (P3, story 6)
├── graph/               # Algorithmes sur l'IR : cycles/SCC, atteignabilité,
│                        #   tri déterministe (networkx confiné ici)
├── insights/
│   ├── metrics.py       # complexité, taille, couplage, couverture doc (story 3)
│   ├── deadcode.py      # code probablement mort + confiance (story 3)
│   ├── entrypoints/     # reconnaisseurs par framework + call graphs (story 2)
│   ├── architecture.py  # couches, composants, violations (story 5)
│   └── patterns.py      # design patterns + indices (story 5)
├── renderers/
│   ├── mermaid/         # classes, dépendances, flux (adapté de gendoc)
│   └── svg.py           # export optionnel [svg]
├── site/
│   ├── builder.py       # génération mkdocs.yml + pages (adapté de gendoc)
│   ├── templates/       # Jinja2 : référence API, santé, architecture, monorepo
│   └── assets/          # mermaid.min.js vendorisé, CSS
├── monorepo/            # détection sous-projets par manifestes (story 6)
├── report/              # rapport d'exécution : console Rich + JSON (FR-020)
├── api.py               # façade bibliothèque publique (constitution II)
├── config.py            # codeatlas.toml / [tool.codeatlas], exclusions par défaut
└── cli.py               # Click : build / check / diagram

tests/
├── unit/                # par module, TDD
├── integration/         # bout en bout sur examples/, double-run, zéro-réseau
└── golden/              # sorties de référence versionnées (mmd, md, json)

examples/
├── python-demo/         # héritages, cycles, patterns, code mort, fichier invalide
├── ts-demo/             # (story 6)
├── java-demo/           # (story 6)
└── monorepo-demo/       # front TS + back Python + service Java (story 6)

action/                  # GitHub Action composite (story 4)
pyproject.toml           # packaging PyPI, extras, ruff/mypy/pytest config
```

**Structure Decision**: projet unique bibliothèque+CLI (Option 1 adaptée). La
séparation `analyzers / ir / insights / renderers / site` matérialise la constitution
III : le dossier `ir/` n'importe aucun analyseur, et `insights/`, `renderers/`,
`site/` n'importent que `ir/` et `graph/`. Chaque user story correspond à des modules
identifiés ci-dessus, livrables indépendamment.

## Complexity Tracking

Aucune violation constitutionnelle — section vide.
