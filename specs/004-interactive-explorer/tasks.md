# Tasks: Explorateur interactif

**Input**: Design documents from `/specs/004-interactive-explorer/`

**Tests**: INCLUS — test-first (constitution V).

---

## Phase 1: Setup

- [x] T001 Packages src/codeatlas/explorer/ et src/codeatlas/serve/ (`__init__.py`) ; section `[explorer]` (enabled=true, include_source=true, default_metric="complexity") dans src/codeatlas/config.py ; `watchdog` en dépendance directe dans pyproject.toml
- [x] T002 [P] Vendoriser cytoscape.min.js (version épinglée) dans src/codeatlas/site/assets/js/vendor/ + test d'intégrité SHA-256 dans tests/unit/test_vendor_integrity.py

## Phase 2: Fondations (bloquant toutes les stories)

- [x] T003 [P] Tests de l'émetteur canonique (JSON canonique : clés/listes triées, séparateurs fixes, LF final ; `schema_version` ; `window.__ATLAS__` ; write → chemins triés ; déterminisme octet pour octet) dans tests/unit/test_emit.py
- [x] T004 ExplorerData + émission `atlas-*.js` (JSON canonique) dans src/codeatlas/explorer/emit.py

**Checkpoint**: fondations prêtes — les stories peuvent démarrer.

## Phase 3: User Story 1 - Explorateur de graphe (P1) 🎯 MVP

**Goal**: vue d'architecture explorable multi-niveaux (zoom, fiche au clic, filtres dans l'URL) avec repli statique.

**Independent Test**: quickstart §1 (explorateur) + §2 (sans JS) + §3 (`file://`) sur monorepo-demo.

- [x] T005 [P] [US1] Tests GraphView (agrégation project→layer→module, `parent` cohérent, arêtes pondérées de même niveau, `certain` propagé, tri, `degraded`, `page` valides) dans tests/unit/test_graphview.py
- [x] T006 [P] [US1] Tests layout hiérarchique (coordonnées entières, déterminisme strict, rangs topologiques respectés, pas de chevauchement de nœuds d'un même niveau) dans tests/unit/test_layout.py
- [x] T007 [US1] GraphView multi-niveaux depuis CodeGraph + insights dans src/codeatlas/explorer/graphview.py
- [x] T008 [US1] Layout déterministe (rangs + barycentre à itérations fixes, entiers) dans src/codeatlas/explorer/layout.py
- [x] T009 [US1] JS explorateur (montage Cytoscape sur positions fournies, fiche latérale, dépliage, filtres lang/couche/sous-projet encodés dans `location.hash`, refus poli si `schema_version` inconnu → repli statique) dans src/codeatlas/site/assets/js/atlas-explorer.js
- [x] T010 [US1] Intégration site : page architecture = contenu statique actuel + conteneur explorateur ; builder branche `build_explorer_data`/émission des assets et données ; option `--no-explorer` + `[explorer] enabled` ; i18n — dans src/codeatlas/site/builder.py, src/codeatlas/site/templates/architecture.md.j2, src/codeatlas/site/i18n.py, src/codeatlas/cli.py, src/codeatlas/api.py
- [x] T011 [P] [US1] Golden atlas-graph.js (corpus python-demo et monorepo-demo) dans tests/golden/test_explorer_golden.py + test intégration build (assets présents, déterminisme deux builds, `--no-explorer` ≡ site actuel) dans tests/integration/test_build_explorer.py

**Checkpoint**: US1 livrable seule (MVP).

## Phase 4: User Story 2 - Recherche de symboles (P2)

**Goal**: recherche instantanée hors-ligne depuis toute page, classement déterministe, jamais d'invention.

**Independent Test**: quickstart §1 (recherche) sur python-demo ; terme inexistant → « aucun résultat ».

- [x] T012 [P] [US2] Tests index de recherche (une entrée par module/classe/fonction/méthode, tri (name, qualname), homonymes désambiguïsés, signatures, cibles `page` valides, déterminisme) dans tests/unit/test_search_index.py
- [x] T013 [US2] Index SearchEntry depuis CodeGraph dans src/codeatlas/explorer/search.py + émission atlas-search.js via emit.py
- [x] T014 [US2] JS recherche (surcouche barre de recherche sur toute page : classement préfixe exact > préfixe > sous-chaîne puis lexicographique, navigation clavier, état vide explicite) dans src/codeatlas/site/assets/js/atlas-search.js + intégration builder/i18n
- [x] T015 [P] [US2] Golden atlas-search.js (python-demo) dans tests/golden/test_explorer_golden.py

**Checkpoint**: US1 + US2 indépendamment fonctionnelles.

## Phase 5: User Story 3 - Mode atelier (P2)

**Goal**: `codeatlas serve` — site servi en local, régénération incrémentale au fil des sauvegardes, auto-reload, tolérance aux fichiers cassés.

**Independent Test**: quickstart §5 (session complète) + §6 (convergence) sur python-demo.

- [x] T016 [P] [US3] Tests invalidation (fichier modifié → éléments → dépendants directs → pages/données à réémettre ; suppression et renommage ; fichier inconnu → build ciblé sans crash) dans tests/unit/test_invalidate.py
- [x] T017 [P] [US3] Tests session (debounce regroupant les rafales, dernière version fait foi, erreur d'analyse → warning sans arrêt, retrait du warning après correction, `build_token` monotone, convergence : N cycles ≡ build à froid octet pour octet) dans tests/unit/test_session.py
- [x] T018 [US3] Invalidation depuis la provenance IR dans src/codeatlas/serve/invalidate.py + watcher watchdog injectable dans src/codeatlas/serve/watcher.py
- [x] T019 [US3] WorkshopSession (cycle pending→rebuilding→idle, réanalyse partielle, fusion IR, réémission ciblée, warnings) dans src/codeatlas/serve/session.py
- [x] T020 [US3] Serveur HTTP local (ThreadingHTTPServer bind 127.0.0.1, MIME corrects, `GET /__atlas_build__`, PortInUseError) + injection du script de polling uniquement dans le site servi (jamais sur disque committable) dans src/codeatlas/serve/server.py
- [x] T021 [US3] api.serve_docs + commande `codeatlas serve` (--port/--open/--watch/--json JSON Lines, codes retour 0/2/4/5) dans src/codeatlas/api.py et src/codeatlas/cli.py
- [x] T022 [P] [US3] Tests intégration serve (port éphémère : site servi, jeton change après événement injecté, port occupé → code 4, --no-watch, arrêt propre) dans tests/integration/test_serve.py

**Checkpoint**: US1-US3 indépendamment fonctionnelles.

## Phase 6: User Story 4 - Tableau de bord explorable (P3)

**Goal**: métriques triables/filtrables, treemap SVG cliquable, avertissements visibles.

**Independent Test**: quickstart §1 (tableau de bord) sur monorepo-demo (tri exact, clic treemap → fiche, fichiers invalides listés).

- [x] T023 [P] [US4] Tests dashboard (rows triées aux clés homogènes, warnings inclus avec motif) et treemap squarify (rectangles entiers, somme des aires ∝ valeurs, ordre et layout déterministes, cellules → pages valides) dans tests/unit/test_dashboard.py
- [x] T024 [US4] DashboardData + treemap + rendu SVG cliquable dans src/codeatlas/explorer/dashboard.py + émission atlas-dashboard.js/SVG via emit.py
- [x] T025 [US4] JS tri de tables (stable, types numériques/texte) dans src/codeatlas/site/assets/js/atlas-tables.js + template health enrichi (table triable + treemap + section fichiers ignorés) dans src/codeatlas/site/templates/health.md.j2 + builder/i18n
- [x] T026 [P] [US4] Golden atlas-dashboard.js + treemap SVG (monorepo-demo) dans tests/golden/test_explorer_golden.py

## Phase 7: User Story 5 - De la fiche au code source (P3)

**Goal**: extraits de source exacts sur les fiches, appelants/appelés cliquables avec certitude distinguée.

**Independent Test**: quickstart §1 (fiche d'une fonction) sur python-demo.

- [x] T027 [P] [US5] Tests extraits (lignes exactes depuis l'IR, `include_source=false` → aucun extrait nulle part, fichier illisible → mention explicite, encodage exotique toléré) dans tests/unit/test_source_excerpt.py
- [x] T028 [US5] SourceExcerpt dans src/codeatlas/explorer/source.py + fiches enrichies (extrait replié `<details>` colorisé, listes appelants/appelés cliquables avec liens incertains marqués) dans src/codeatlas/site/pages.py et src/codeatlas/site/templates/module.md.j2 + option `[explorer] include_source`

## Phase 8: Polish & transversal

- [x] T029 Test zéro-ressource-externe (aucune URL http(s) externe dans le site généré, y compris JS vendorisé) + extension du test no-network au mode serve (aucune socket sortante) dans tests/integration/test_no_network.py
- [x] T030 README (section « Explorer la documentation »), quickstart 004 exécuté de bout en bout, couverture ≥ 80 %, ruff + mypy propres, mesure SC-005 (build ≤ +20 % vs --no-explorer sur monorepo-demo)

## Phase 9: Convergence (post-/speckit-analyze)

- [x] T031 [US4] Filtre texte au-dessus des tables (masquage des lignes sans correspondance, fr/en) dans src/codeatlas/site/assets/atlas-tables.js + tripwire dans tests/unit/test_vendor_integrity.py per FR-013 (analyse C1)
- [x] T032 Retrait de `metrics_available` (donnée morte) du payload dashboard dans src/codeatlas/explorer/dashboard.py ; FR-014 reformulé (métrique choisie par configuration) per analyse C2
- [x] T033 Test de garde du surcoût explorateur (ratio build explorer / --no-explorer < 1.35, marqueur slow) dans tests/integration/test_performance.py per SC-005 (analyse C3) ; couverture manuelle SC-001/002/006/007 consignée dans plan.md (analyse C4)

---

## Dependencies

- Setup (T001-T002) → Fondations (T003-T004) → toutes les stories.
- US1 (T005-T011) : MVP, ne dépend que des fondations.
- US2 (T012-T015) : indépendante de US1 (partage emit.py) ; l'UI s'intègre au même builder.
- US3 (T016-T022) : réutilise le build complet (US1 incluse de fait) ; testable dès les fondations via builds ciblés.
- US4 (T023-T026) et US5 (T027-T028) : indépendantes entre elles, après fondations.
- Polish (T029-T030) : après les stories retenues.

## Parallel opportunities

- T002 ∥ T001 ; T003 ∥ T001-T002.
- Dans chaque story, les tâches de tests marquées [P] s'écrivent en parallèle (fichiers distincts) et AVANT l'implémentation (échec vérifié).
- Après la Phase 2 : US1, US2, US4, US5 parallélisables (fichiers disjoints, sauf goldens partagés tests/golden/test_explorer_golden.py — à sérialiser entre stories).

## Implementation Strategy

MVP = Phases 1-3 (US1) : livrable et démontrable seul. Puis US2 (valeur immédiate,
petite), US3 (la plus grosse, forte valeur), US4, US5, Polish. Arrêt possible à
chaque checkpoint avec un site cohérent.
