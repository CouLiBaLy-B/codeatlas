# Tasks: CodeAtlas — Générateur de documentation intelligente

**Input**: Design documents from `/specs/001-intelligent-doc-generator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUS — la constitution (principe V) impose le test-first : chaque tâche de
test est écrite et validée EN ÉCHEC avant la tâche d'implémentation correspondante.

**Organization**: tâches groupées par user story (US1–US6) ; chaque story est un
incrément livrable et testable indépendamment.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : parallélisable (fichiers différents, aucune dépendance sur une tâche inachevée)
- **[Story]** : US1–US6, mappées sur spec.md
- Chemins relatifs à la racine du repo `codeatlas/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: squelette du projet, outillage qualité, CI

- [x] T001 Créer le packaging : pyproject.toml (nom `codeatlas`, Python ≥ 3.11, deps cœur click/rich/jinja2/networkx, extras `[site]`, `[javascript]`, `[java]`, `[svg]`, `[all]`, `[dev]`, entry point CLI), LICENSE MIT, .gitignore, `src/codeatlas/__init__.py` avec `__version__`
- [x] T002 [P] Configurer ruff (lint+format), mypy strict et pytest/pytest-cov (fail-under 80) dans pyproject.toml
- [x] T003 [P] Créer l'arborescence des packages avec `__init__.py` : src/codeatlas/{ir,analyzers,analyzers/python,graph,insights,insights/entrypoints,renderers,renderers/mermaid,site,site/templates,site/assets,monorepo,report}/ et tests/{unit,integration,golden}/
- [x] T004 [P] CI GitHub Actions dans .github/workflows/ci.yml : ruff + mypy + pytest-cov sur Python 3.11/3.12, Linux + Windows

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: l'IR, les algorithmes de graphe, la config, les contrats de base — tout ce
que TOUTES les stories consomment (constitution III)

**⚠️ CRITICAL**: aucune story ne démarre avant la fin de cette phase

- [x] T005 [P] Tests unitaires du modèle IR (construction, invariants — arêtes vers nœuds existants, ids uniques, itération triée — et JSON canonique) dans tests/unit/test_ir.py
- [x] T006 Modèle IR : dataclasses gelées CodeGraph/SubProject/Node/Edge/SkippedFile, enums NodeKind/EdgeKind/Certainty (contrats ir-schema.md, data-model.md) dans src/codeatlas/ir/model.py
- [x] T007 Sérialisation JSON canonique de l'IR (`ir_version`, clés triées, UTF-8, champs vides omis) dans src/codeatlas/ir/serialize.py
- [x] T008 [P] Tests unitaires algorithmes de graphe (cycles/SCC, atteignabilité, tri déterministe) dans tests/unit/test_graph.py
- [x] T009 Algorithmes de graphe sur l'IR — networkx confiné ici (constitution : plan.md) dans src/codeatlas/graph/algorithms.py
- [x] T010 [P] Tests unitaires configuration (fusion défauts/fichier/CLI, clé inconnue → erreur avec suggestion, valeurs hors domaine) dans tests/unit/test_config.py
- [x] T011 Chargeur de configuration TOML (`codeatlas.toml` / `[tool.codeatlas]`, schéma et défauts de config-schema.md, exclusions par défaut) dans src/codeatlas/config.py
- [x] T012 Contrat LanguageAnalyzer + registre + découverte/lecture des fichiers (SourceFile, AnalyzerOptions, IRFragment, encodage géré → skipped, extras absents → message actionnable) dans src/codeatlas/analyzers/base.py
- [x] T013 Modèle AnalysisReport + rendu console Rich (compteurs, skipped, warnings — durée jamais dans les artefacts) dans src/codeatlas/report/model.py et src/codeatlas/report/render.py
- [x] T014 Façade API publique (signatures analyze/build_site/render_diagram/run_checks du contrat analyzer-protocol.md, câblage registre) dans src/codeatlas/api.py
- [x] T015 Squelette CLI Click (groupe, politique stdout/stderr, exit codes 0/1/2/3 du contrat cli.md) dans src/codeatlas/cli.py

**Checkpoint**: fondations prêtes — les user stories peuvent démarrer

---

## Phase 3: User Story 1 - Documenter un dépôt Python en une commande (Priority: P1) 🎯 MVP

**Goal**: `codeatlas build ./repo` sur un dépôt Python → site MkDocs Material complet
(vue d'ensemble, diagrammes de classes, dépendances de packages avec cycles, référence
API, section éléments non analysés), hors-ligne et déterministe.

**Independent Test**: quickstart.md § « Validation P1 » + « Déterminisme et hors-ligne »
sur examples/python-demo.

### Tests for User Story 1 (test-first ⚠️ échec avant implémentation)

- [x] T016 [P] [US1] Construire le corpus examples/python-demo/ : packages avec héritages, composition, cycle de packages volontaire, docstrings Google, visibilités mixtes, fichier invalid_syntax.py volontaire
- [x] T017 [P] [US1] Tests contrat de l'analyseur Python (nœuds/arêtes attendus sur le corpus, ids stables, certitudes, skipped, tri) dans tests/unit/test_python_analyzer.py
- [x] T018 [P] [US1] Golden tests diagrammes de classes Mermaid (références .mmd versionnées) dans tests/golden/test_class_diagram.py
- [x] T019 [P] [US1] Golden tests diagramme de dépendances de packages avec cycle surligné dans tests/golden/test_package_deps.py
- [x] T020 [P] [US1] Golden tests pages de référence API générées depuis l'IR dans tests/golden/test_api_pages.py
- [x] T021 [P] [US1] Test d'intégration bout en bout des 4 scénarios d'acceptation US1 (site complet, cycle mis en évidence, fichier invalide listé + exit 0, double run identique) + assertion SC-003 : 100 % des classes/fonctions publiques du corpus présentes dans la référence API, dans tests/integration/test_build_python.py
- [x] T022 [P] [US1] Test déterminisme générique (double exécution → diff binaire vide) dans tests/integration/test_determinism.py
- [x] T023 [P] [US1] Test zéro-réseau (socket bloquée pendant tout le build — SC-007) dans tests/integration/test_no_network.py

### Implementation for User Story 1

- [x] T024 [US1] Analyseur Python ast → fragment d'IR (classes/fonctions/attributs, héritage, composition/agrégation/association, imports, docstrings, signatures, modifiers, loc — adapté de gendoc) dans src/codeatlas/analyzers/python/analyzer.py
- [x] T025 [US1] Complexité cyclomatique Python (définition commune d'ir-schema.md, attribut du nœud IR) dans src/codeatlas/analyzers/python/complexity.py
- [x] T026 [US1] Renderer Mermaid diagrammes de classes (tri, échappement, styles par type d'arête) dans src/codeatlas/renderers/mermaid/class_diagram.py
- [x] T027 [US1] Renderer Mermaid dépendances de packages + cycles surlignés (via graph/algorithms) dans src/codeatlas/renderers/mermaid/package_deps.py
- [x] T028 [US1] Templates Jinja2 de la référence API (index, page module, macros symboles/signatures/doc) dans src/codeatlas/site/templates/ — libellés du site externalisés dans src/codeatlas/site/i18n.py (en + fr, sélection par `project.language` — FR-017)
- [x] T029 [US1] Vendoriser mermaid.min.js dans src/codeatlas/site/assets/ (package data + copie dans le site — R4)
- [x] T030 [US1] Builder du site MkDocs Material (mkdocs.yml généré, nav triée, SuperFences mermaid local, section « éléments non analysés », remplacement atomique de --out, préservation extra_nav, toutes écritures en UTF-8 avec fins de ligne `\n` — déterminisme cross-OS) dans src/codeatlas/site/builder.py
- [x] T031 [US1] Câbler api.analyze et api.build_site de bout en bout (découverte → analyseur → IR → renderers → site → AnalysisReport) dans src/codeatlas/api.py
- [x] T032 [US1] Commande `codeatlas build` complète (toutes les options du contrat cli.md, --no-site, --json-report) dans src/codeatlas/cli.py

**Checkpoint**: MVP fonctionnel — publiable et démontrable seul

---

## Phase 4: User Story 2 - Comprendre les flux d'exécution (Priority: P2)

**Goal**: points d'entrée détectés (main, CLI, routes) + graphes d'appels/flux Mermaid à
profondeur réglable, liens incertains distingués ; commande `codeatlas diagram`.

**Independent Test**: quickstart.md § « Validation P2 — Graphes d'appels » sur le corpus.

### Tests for User Story 2 (test-first ⚠️)

- [x] T033 [P] [US2] Enrichir examples/python-demo/ : CLI Click factice, routes FastAPI factices, chaînes d'appels profondes, appels dynamiques (getattr) pour les cas `inferred`
- [x] T034 [P] [US2] Tests résolution d'appels (locaux, importés, méthodes → `certain` ; dynamiques → `inferred` ; non résolus comptés) dans tests/unit/test_call_resolution.py
- [x] T035 [P] [US2] Tests reconnaisseurs de points d'entrée Python (main, click, fastapi) dans tests/unit/test_entrypoints.py
- [x] T036 [P] [US2] Golden tests diagrammes de flux (profondeur exacte, pointillés inferred, légende) dans tests/golden/test_call_flow.py
- [x] T037 [P] [US2] Test d'intégration des 3 scénarios d'acceptation US2 dans tests/integration/test_call_graphs.py

### Implementation for User Story 2

- [x] T038 [US2] Extraction des appels dans l'analyseur Python (table des symboles importés, arêtes `calls` avec certitude — R6) dans src/codeatlas/analyzers/python/calls.py
- [x] T039 [US2] Registre EntryPointRecognizer + reconnaisseurs Python (`__main__`, click/typer/argparse, fastapi/flask/django) dans `src/codeatlas/insights/entrypoints/__init__.py` et src/codeatlas/insights/entrypoints/python.py
- [x] T040 [US2] Renderer Mermaid call flow (BFS borné par --depth, style inferred, légende) dans src/codeatlas/renderers/mermaid/call_flow.py
- [x] T041 [US2] Pages « Points d'entrée » dans le site (template + intégration builder) dans src/codeatlas/site/templates/entrypoints.md.j2
- [x] T042 [US2] Commande `codeatlas diagram` (--type class|deps|calls, --focus, --depth, sortie stdout/.mmd) + api.render_diagram dans src/codeatlas/cli.py

**Checkpoint**: US1 + US2 fonctionnelles indépendamment

---

## Phase 5: User Story 3 - Évaluer la santé du code (Priority: P2)

**Goal**: page « Santé du code » — complexité, taille, couplage, couverture doc, code
probablement mort avec confiance ; statuts visuels ok/warn/critical.

**Independent Test**: quickstart.md § « Validation P2 — Santé du code ».

### Tests for User Story 3 (test-first ⚠️)

- [x] T043 [P] [US3] Enrichir examples/python-demo/ : fonction volontairement complexe (> 20), fonctions non documentées, fonction morte privée + fonction morte publique (confiances différentes)
- [x] T044 [P] [US3] Tests métriques avec valeurs exactes attendues sur le corpus (complexité, loc, fan-in/out, doc coverage, statuts seuils) dans tests/unit/test_metrics.py
- [x] T045 [P] [US3] Tests code mort (atteignabilité + références, niveaux de confiance) dans tests/unit/test_deadcode.py
- [x] T046 [P] [US3] Test d'intégration des 3 scénarios d'acceptation US3 (dont déterminisme des métriques) dans tests/integration/test_health.py

### Implementation for User Story 3

- [x] T047 [US3] Insight metrics (agrégations par module, statuts par seuils configurables — R5) dans src/codeatlas/insights/metrics.py
- [x] T048 [US3] Insight deadcode (non-atteignable depuis les points d'entrée ET sans référence entrante, confiance dégradée si public/exporté — R7) dans src/codeatlas/insights/deadcode.py
- [x] T049 [US3] Page « Santé du code » (tableaux triés, statuts visuels, liens vers les symboles) dans src/codeatlas/site/templates/health.md.j2 + intégration builder

**Checkpoint**: US1–US3 fonctionnelles indépendamment

---

## Phase 6: User Story 4 - Documentation toujours à jour via la CI (Priority: P2)

**Goal**: `codeatlas check` avec seuils (exit 3 si violation), rapport JSON stable,
GitHub Action officielle qui build + publie sur Pages.

**Independent Test**: quickstart.md § « Validation P2 — Mode CI ».

### Tests for User Story 4 (test-first ⚠️)

- [x] T050 [P] [US4] Tests mode check (chaque seuil : passe/échoue, exit codes, cumul des violations) dans tests/unit/test_check.py
- [x] T051 [P] [US4] Golden test du schéma AnalysisReport JSON (report_version, clés triées, duration exclue de la comparaison) dans tests/golden/test_report_json.py
- [x] T052 [P] [US4] Test d'intégration scénario US4 (build → modification du corpus → check détecte la régression) dans tests/integration/test_check_mode.py

### Implementation for User Story 4

- [x] T053 [US4] Évaluation des seuils + api.run_checks (max_package_cycles, min_doc_coverage, max_critical_symbols) dans src/codeatlas/insights/checks.py
- [x] T054 [US4] Commande `codeatlas check` (options du contrat cli.md, exit 3, --json-report) dans src/codeatlas/cli.py
- [x] T055 [US4] Export AnalysisReport JSON conforme au schéma de cli.md dans src/codeatlas/report/json.py
- [x] T056 [US4] GitHub Action composite (install + build + upload Pages, inputs path/config/out) dans action/action.yml + doc d'usage action/README.md

**Checkpoint**: US1–US4 fonctionnelles indépendamment

---

## Phase 7: User Story 5 - Visualiser l'architecture et les patterns (Priority: P3)

**Goal**: vue « Architecture » (couches, composants, violations) et détection de
patterns (Singleton, Factory, Observer, Adapter, Decorator), chaque détection justifiée
par des indices.

**Independent Test**: quickstart.md § « Validation P3 — Architecture & patterns ».

### Tests for User Story 5 (test-first ⚠️)

- [x] T057 [P] [US5] Corpus examples/layered-demo/ (corpus séparé pour préserver les goldens de python-demo) : couches api/domain/infra nommées, violation volontaire (infra → api), patterns implémentés + contre-exemples proches (faux positifs à éviter — SC-008)
- [x] T058 [P] [US5] Tests détection couches/composants/violations (avec evidence obligatoire) dans tests/unit/test_architecture.py
- [x] T059 [P] [US5] Tests détection patterns (vrais positifs + non-détection des contre-exemples) dans tests/unit/test_patterns.py
- [x] T060 [P] [US5] Test d'intégration des 3 scénarios d'acceptation US5 dans tests/integration/test_architecture_view.py

### Implementation for User Story 5

- [x] T061 [US5] Insight architecture (couches par nommage × direction des dépendances, composants par communautés, violations — R7) dans src/codeatlas/insights/architecture.py
- [x] T062 [US5] Insight patterns (5 patterns v1 par signatures structurelles sur l'IR, indices) dans src/codeatlas/insights/patterns.py
- [x] T063 [US5] Vue « Architecture » : renderer Mermaid (couches + violations en rouge) et templates (page architecture, mention patterns sur pages classes) dans src/codeatlas/renderers/mermaid/architecture.py et src/codeatlas/site/templates/architecture.md.j2

**Checkpoint**: US1–US5 fonctionnelles indépendamment

---

## Phase 8: User Story 6 - Documenter un monorepo polyglotte (Priority: P3)

**Goal**: analyseurs JS/TS et Java (tree-sitter), détection des sous-projets par
manifestes, site unique avec navigation croisée et graphe inter-services.

**Independent Test**: quickstart.md § « Validation P3 — Monorepo polyglotte ».

### Tests for User Story 6 (test-first ⚠️)

- [x] T064 [P] [US6] Corpus examples/ts-demo/ : classes/interfaces TS, imports, routes Express factices, JSDoc, fichier invalide volontaire
- [x] T065 [P] [US6] Corpus examples/java-demo/ : classes/interfaces, héritage, contrôleur Spring factice, Javadoc, main
- [x] T066 [P] [US6] Corpus examples/monorepo-demo/ : front TS + back Python + service Java + sous-dossier langage inconnu, dépendances croisées déclarées dans les manifestes
- [x] T067 [P] [US6] Tests contrat analyseur JS/TS (mêmes exigences que T017) dans tests/unit/test_js_analyzer.py
- [x] T068 [P] [US6] Tests contrat analyseur Java dans tests/unit/test_java_analyzer.py
- [x] T069 [P] [US6] Tests détection de sous-projets (manifestes, non-chevauchement, langage inconnu) dans tests/unit/test_monorepo.py
- [x] T070 [P] [US6] Test d'intégration des 3 scénarios d'acceptation US6 (site unique, graphe inter-services, sous-projet inconnu listé) dans tests/integration/test_monorepo_build.py

### Implementation for User Story 6

- [x] T071 [US6] Analyseur JavaScript/TypeScript tree-sitter → IR (classes, fonctions, imports, appels, JSDoc, complexité) dans src/codeatlas/analyzers/javascript/analyzer.py
- [x] T072 [US6] Analyseur Java tree-sitter → IR (classes, interfaces, héritage/implémentation, imports, appels, Javadoc, complexité) dans src/codeatlas/analyzers/java/analyzer.py
- [x] T073 [US6] Détection monorepo par manifestes + arêtes `service_dep` depuis les dépendances déclarées (R8) dans src/codeatlas/monorepo/detect.py
- [x] T074 [US6] Reconnaisseurs de points d'entrée JS/TS (express/nest, bin) et Java (main, spring-web, JAX-RS) dans src/codeatlas/insights/entrypoints/javascript.py et src/codeatlas/insights/entrypoints/java.py
- [x] T075 [US6] Vue monorepo unifiée : graphe inter-services Mermaid + navigation croisée dans le builder dans src/codeatlas/renderers/mermaid/services.py et src/codeatlas/site/templates/monorepo.md.j2

**Checkpoint**: toutes les stories fonctionnelles indépendamment

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: finitions transverses, performance, publication

- [x] T076 [P] README.md complet (installation, usage, exemples, badges) + dogfooding : `codeatlas build` sur CodeAtlas lui-même publié en démo
- [x] T077 [P] Benchmark de performance (générer un corpus synthétique ~50k lignes, vérifier < 30 s — SC-001 ; machine de référence = runner GitHub Actions ubuntu-latest standard) dans tests/integration/test_performance.py (marqueur `slow`)
- [x] T078 Préparation release : vérification build sdist/wheel, installation de chaque extra dans un venv propre, publication TestPyPI
- [x] T079 Exécuter intégralement quickstart.md et corriger tout écart constaté
- [x] T080 Audit final constitution : couverture ≥ 80 %, double-run octet pour octet sur les 3 corpus, zéro réseau, aucune fuite de chemin absolu dans les artefacts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : aucune dépendance
- **Foundational (Phase 2)** : dépend de Setup — BLOQUE toutes les stories
- **US1 (Phase 3)** : dépend de Foundational — aucune dépendance de story
- **US2 (Phase 4)** : dépend de Foundational + T024 (analyseur Python) et T030 (builder) d'US1
- **US3 (Phase 5)** : dépend de Foundational + T024/T030 ; le code mort (T048) exploite les points d'entrée d'US2 s'ils existent (sinon repli : références seules)
- **US4 (Phase 6)** : dépend de Foundational + US1 (build) ; indépendante d'US2/US3 (les seuils absents sont simplement non vérifiés)
- **US5 (Phase 7)** : dépend d'US1 + arêtes `calls` d'US2
- **US6 (Phase 8)** : dépend d'US1 (chaîne complète) ; réutilise US2–US5 pour les nouveaux langages sans les modifier (tout passe par l'IR)
- **Polish (Phase 9)** : dépend des stories retenues

### Within Each User Story

- Corpus et tests d'abord (échec vérifié), puis implémentation, puis checkpoint
- Les golden files sont créés au premier run validé manuellement puis figés

### Parallel Opportunities

- Phase 1 : T002, T003, T004 en parallèle après T001
- Phase 2 : les paires test/impl (T005+T006, T008+T009, T010+T011) sur des fichiers disjoints ; T012–T015 séquentiels après T006
- Dans chaque story : toutes les tâches de tests [P] en parallèle ; corpus [P] indépendants
- Après US1 : US2, US3, US4 peuvent être menées en parallèle (fichiers disjoints)
- Phase 8 : les deux analyseurs T071 et T072 en parallèle

## Parallel Example: User Story 1

```bash
# Corpus + tous les tests d'US1 ensemble (avant toute implémentation) :
Task: "T016 corpus examples/python-demo"
Task: "T017 tests analyseur dans tests/unit/test_python_analyzer.py"
Task: "T018 golden classes dans tests/golden/test_class_diagram.py"
Task: "T019 golden dépendances dans tests/golden/test_package_deps.py"
Task: "T020 golden API dans tests/golden/test_api_pages.py"
Task: "T021-T023 tests d'intégration dans tests/integration/"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1)
2. **STOP et VALIDER** : quickstart § P1 + déterminisme + hors-ligne
3. Démo/publication possible dès ce point (équivalent gendoc, ré-architecturé)

### Incremental Delivery

1. US1 (MVP Python) → 2. US2 (flux) → 3. US3 (santé) → 4. US4 (CI) → 5. US5
(architecture) → 6. US6 (multi-langage/monorepo) — chaque incrément est validé par son
checkpoint quickstart avant de passer au suivant, sans casser les précédents (golden
files en garde-fou).

---

## Phase 10: Convergence

**Purpose**: écarts constatés par /speckit-converge entre le code et la spec/plan/contrats
(2 HIGH, 3 MEDIUM, 2 LOW — aucune violation constitutionnelle)

- [x] T081 Préserver les pages manuelles référencées par `[site].extra_nav` lors de la régénération (le remplacement atomique de --out les écrase aujourd'hui) dans src/codeatlas/site/builder.py per spec Assumptions + contrat cli.md « jamais écrasées » (contradicts)
- [x] T082 Implémenter l'export SVG des diagrammes (`--svg`, `[site].svg_export`, extra `[svg]`) ou retirer l'option et l'extra tant que non supportés — l'option est aujourd'hui silencieusement sans effet — dans src/codeatlas/site/builder.py et src/codeatlas/cli.py per FR-014 / R4 (partial)
- [x] T083 Extraire les arêtes `calls` dans les analyseurs JS/TS et Java afin que les diagrammes de flux de leurs points d'entrée ne soient plus vides, dans src/codeatlas/analyzers/javascript/analyzer.py et src/codeatlas/analyzers/java/analyzer.py per FR-009 (partial)
- [x] T084 Honorer `--depth` pour `diagram --type class` : rendre le voisinage à rayon N autour de la classe focale (relations inter-modules incluses) au lieu du module entier, dans src/codeatlas/api.py et src/codeatlas/renderers/mermaid/class_diagram.py per FR-010 / contrat cli.md (partial)
- [x] T085 Détecter les imports croisés entre sous-projets et restituer la nature des liens (déclaré vs import) dans le graphe inter-services, dans src/codeatlas/monorepo/detect.py et src/codeatlas/renderers/mermaid/services.py per R8 / US6-AC2 (partial)
- [x] T086 Implémenter `[monorepo].roots` (forcer des racines de sous-projets, surcharge de la détection) — clé validée mais sans effet — dans src/codeatlas/monorepo/detect.py per contrat config-schema.md (partial)
- [x] T087 Appliquer le filtre `[analysis].languages` dans le mode monorepo (_analyze_monorepo l'ignore), dans src/codeatlas/api.py per FR-017 (partial)
