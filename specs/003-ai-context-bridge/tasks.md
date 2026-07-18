# Tasks: Pont IA

**Input**: Design documents from `/specs/003-ai-context-bridge/`

**Tests**: INCLUS — test-first (constitution V).

---

## Phase 1: Setup

- [x] T001 Package src/codeatlas/bridge/ (`__init__.py`) ; section `[export] budget = 24000` (validation ≥ 2000) dans src/codeatlas/config.py ; extra `mcp = ["mcp>=1.2"]` dans pyproject.toml (+ `[all]`)

## Phase 2: User Story 1 - Carte du dépôt (P1)

- [x] T002 [P] [US1] Tests repomap (priorisation modules à entrées puis fan-in, budget respecté, module entier ou rien, omissions explicites, budget trop petit → erreur, déterminisme) dans tests/unit/test_repomap.py
- [x] T003 [P] [US1] Golden test de la carte du corpus python-demo dans tests/golden/test_repomap_golden.py
- [x] T004 [US1] RepoMap (priorisation, budget, rendu markdown) dans src/codeatlas/bridge/repomap.py + api.export_repomap
- [x] T005 [US1] Commande `codeatlas export` (--format repomap|graph, --budget, --out) dans src/codeatlas/cli.py
- [x] T006 [P] [US1] Test intégration export CLI (stdout, --out, format graph = IR JSON, monorepo couvert) dans tests/integration/test_export_cli.py

## Phase 3: User Story 3 - Analyse d'impact (P2)

- [x] T007 [P] [US3] Tests impact (niveaux exacts sur le corpus, points d'entrée atteints marqués, certitude conservée, cible sans référence → vide explicite, fichier → tous ses symboles) dans tests/unit/test_impact.py
- [x] T008 [US3] Insight impact (BFS inverse calls+imports par niveaux) dans src/codeatlas/insights/impact.py + api.compute_impact
- [x] T009 [US3] Commande `codeatlas impact` (--focus symbole|fichier, --depth, --format text|json) dans src/codeatlas/cli.py

## Phase 4: User Story 2 - Serveur MCP (P2)

- [x] T010 [P] [US2] Tests des outils comme fonctions pures (search exact/suffixe/borné, module_api, callers/callees avec certitude, dead_code, overview ; symbole ambigu → candidats ; jamais d'invention) dans tests/unit/test_mcp_tools.py
- [x] T011 [US2] Fonctions outils sur le graphe dans src/codeatlas/bridge/tools.py
- [x] T012 [US2] Serveur FastMCP stdio (import paresseux, message actionnable sans extra) dans src/codeatlas/bridge/server.py + commande `codeatlas mcp`
- [x] T013 [P] [US2] Smoke test serveur (construction, outils enregistrés, skip si extra absent) dans tests/integration/test_mcp_server.py

## Phase 5: User Story 4 - Parcours de lecture (P3)

- [x] T014 [P] [US4] Tests parcours (corpus layered : entrées d'abord puis api→domain→infra, déterminisme) dans tests/unit/test_tour.py
- [x] T015 [US4] Insight tour dans src/codeatlas/insights/tour.py + section repomap + page site (template tour.md.j2, builder, i18n)

## Phase 6: Polish

- [x] T016 README (section « Le substrat pour vos outils IA » + config MCP exemple), quickstart 003 exécuté, couverture ≥ 80 %, ruff, mypy

---

## Dependencies

Setup → US1 → US3 (réutilise le graphe) → US2 (expose US1/US3) → US4 → Polish.

---

## Phase 7: Convergence

- [x] T017 Implémenter le paramètre `depth` de `callers`/`callees` (traversée par niveaux, champ depth par lien) dans src/codeatlas/bridge/tools.py et server.py per contrat bridge.md (partial)
- [x] T018 Test zéro-réseau couvrant export, impact et les outils MCP (socket bloquée) dans tests/integration/test_no_network.py per FR-005/SC-003 (partial)
- [x] T019 Test exhaustif SC-001 : 100 % des symboles publics présents dans la carte au budget par défaut dans tests/unit/test_repomap.py per SC-001 (partial)
- [x] T020 Exposer la fraîcheur d'analyse dans l'outil `overview` du serveur (horodatage capturé au chargement, rechargement via reload) dans src/codeatlas/bridge/server.py per spec edge case (partial)
