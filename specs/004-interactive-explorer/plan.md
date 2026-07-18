# Implementation Plan: Explorateur interactif

**Branch**: `004-interactive-explorer` | **Date**: 2026-07-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-interactive-explorer/spec.md`

## Summary

La documentation générée devient une interface : **explorateur de graphe**
multi-niveaux (pan/zoom/filtres/fiches, positions précalculées au build),
**recherche de symboles** instantanée hors-ligne, **mode atelier**
(`codeatlas serve` : watch + régénération incrémentale + auto-reload local),
**tableau de bord** triable avec treemap SVG cliquable, **fiches → source**
(extraits exacts, appelants/appelés navigables). Principe directeur : toute
l'intelligence est précalculée en Python (déterministe), le navigateur ne fait que
rendre et filtrer ; chaque vue a un repli statique équivalent au rendu actuel.

## Technical Context

**Language/Version**: Python ≥ 3.11 (inchangé) + JavaScript vanilla embarqué (ES2020,
sans build front). **Primary Dependencies**: Cytoscape.js **vendorisé** (version
épinglée, SHA-256 vérifié par test — comme Mermaid) ; `watchdog` promu en dépendance
directe (déjà présent via MkDocs) ; serveur HTTP stdlib ; treemap/layout maison
(networkx pour rangs topologiques). Aucun framework front, aucun CDN. **Storage**:
fichiers du site (`assets/data/atlas-*.js` en JSON canonique, SVG treemap).
**Testing**: pytest test-first ; goldens sur les données de vues et le SVG ;
intégration serve (serveur réel sur port éphémère, événements watch injectés) ;
JS validé par contrat de données + scénarios quickstart. Couverture assumée
comme MANUELLE (quickstart) pour les critères nécessitant un navigateur :
SC-001 (recherche < 5 s), SC-002 (interaction < 200 ms), SC-006 (reload visible
< 5 s), SC-007 (rendu sans scripts) — le projet n'embarque aucun harnais
navigateur ; SC-005 est verrouillé par un test de ratio (garde 1.35). **Target Platform**:
navigateurs récents, y compris consultation `file://` (données en `<script src>`,
jamais `fetch`). **Project Type**: bibliothèque + CLI (inchangé). **Performance
Goals**: SC-002 interaction < 200 ms sur 50 k lignes (positions précalculées, niveau
symbole jamais dans le graphe global) ; SC-005 build ≤ +20 % et < 30 s ; SC-006
reload < 5 s (invalidation incrémentale via provenance IR). **Constraints**:
constitution I–V ; localhost only (bind 127.0.0.1 codé en dur) ; jeton de reload
injecté uniquement en mode serve, jamais dans les artefacts. **Scale/Scope**: dépôts
jusqu'à ~50 k lignes / centaines de modules ; agrégation par niveaux au-delà.

Décisions détaillées et alternatives : [research.md](research.md) (R1–R10).

## Constitution Check

| # | Principe | Évaluation | Verdict |
| --- | --- | --- | --- |
| I | Déterminisme, hors-ligne | layout, treemap et index calculés en Python sans aléa ; JSON canonique ; vendor épinglé + SHA-256 ; aucune ressource externe ; jeton de reload hors artefacts ; convergence atelier ↔ build à froid testée | ✅ |
| II | Bibliothèque d'abord | `build_explorer_data` / `serve_docs` dans `api.py` ; CLI façade (`serve`, `build --no-explorer`) ; `serve --json` scriptable | ✅ |
| III | IR unique | `explorer/` et `serve/` ne consomment que CodeGraph + insights ; le JS ne consomme que les données dérivées ; ajouter un langage ne touche aucune vue (FR-020) | ✅ |
| IV | Tolérance | fichier invalide en mode atelier → avertissement structuré, session vivante ; avertissements visibles dans le tableau de bord ; fiche sans source lisible l'indique | ✅ |
| V | Test-first ≥ 80 % | goldens données/SVG sur corpus existants ; tests d'invalidation, de convergence et de déterminisme écrits avant implémentation | ✅ |

**Re-check post-design** : ✅ — aucune violation, section Complexity Tracking vide.

## Project Structure

### Documentation (this feature)

```text
specs/004-interactive-explorer/
├── plan.md              # ce fichier
├── research.md          # décisions R1–R10
├── data-model.md        # GraphView, SearchEntry, DashboardData, WorkshopSession…
├── quickstart.md        # 8 scénarios de validation de bout en bout
├── contracts/explorer.md # API, CLI serve/build, contrat données ↔ navigateur
└── tasks.md             # produit par /speckit-tasks (pas par /speckit-plan)
```

### Source Code (repository root)

```text
src/codeatlas/
├── explorer/                  # NOUVEAU — construction des données de vues (pur, déterministe)
│   ├── __init__.py
│   ├── graphview.py           # GraphView multi-niveaux (agrégation, arêtes pondérées)
│   ├── layout.py              # layout hiérarchique déterministe (rangs + barycentre)
│   ├── search.py              # index de symboles (SearchEntry)
│   ├── dashboard.py           # DashboardData + treemap squarify (entiers)
│   ├── source.py              # extraits de source (SourceExcerpt, include_source)
│   └── emit.py                # write_data : JSON canonique → assets/data/atlas-*.js
├── serve/                     # NOUVEAU — mode atelier
│   ├── __init__.py
│   ├── session.py             # WorkshopSession : cycle de vie, debounce, convergence
│   ├── invalidate.py          # fichier modifié → éléments IR → dépendants → cibles
│   ├── watcher.py             # watchdog (injectable pour les tests)
│   └── server.py              # ThreadingHTTPServer 127.0.0.1 + /__atlas_build__
├── site/
│   ├── assets/                # cytoscape.min.js épinglé + atlas-{explorer,search,tables}.js
│   ├── templates/             # architecture/health/module enrichis + fiche symbole
│   ├── builder.py             # branchement explorer (enabled/--no-explorer)
│   └── pages.py               # fiches : source, appelants/appelés, ancres de recherche
├── api.py                     # + build_explorer_data / serve_docs
├── cli.py                     # + commande serve ; build --no-explorer
└── config.py                  # + section [explorer]

tests/
├── unit/test_graphview.py, test_layout.py, test_search_index.py,
│   test_dashboard.py, test_source_excerpt.py, test_emit.py, test_vendor_integrity.py,, test_invalidate.py, test_session.py
├── golden/test_explorer_golden.py      # atlas-*.js + SVG sur les corpus
└── integration/test_serve.py           # serveur réel, reload, port occupé, convergence
    integration/test_build_explorer.py  # build complet, déterminisme, --no-explorer
```

**Structure Decision**: deux nouveaux packages, symétriques de l'existant :
`explorer/` produit des artefacts (comme `bridge/`, `baseline/`) et reste pur/testable
sans navigateur ; `serve/` isole tout ce qui est processus vivant (watch, HTTP) pour
que rien de non déterministe n'entre dans le chemin de build. `site/` reste le seul
assembleur MkDocs.

## Complexity Tracking

Aucune violation — section vide.
