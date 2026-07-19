# Tasks: Détection de la racine des sources

**Input**: Design documents from `/specs/005-source-root-detection/`

**Tests**: INCLUS — test-first (constitution V).

---

## Phase 1: Setup

- [x] T001 Corpus versionné `examples/src-layout-demo/` : `src/mypkg/` (package sous `src/`) avec `__init__.py`, modules à imports internes (`core` importe `util`, `models.order` importe `models.product`), pour exercer la détection et la résolution d'arêtes

## Phase 2: User Story 1 - Layout `src/` (P1) 🎯 MVP

**Goal**: déduire la racine d'import et nommer les modules `mypkg.*`, résoudre les imports en arêtes.

**Independent Test**: quickstart §1 (arêtes > 0 sur src-layout-demo et sur CodeAtlas) + §2 (python-demo inchangé).

- [x] T002 [P] [US1] Tests de `detect_import_roots` (layout `src/` → racine `src` ; package à la racine → racine vide ; déterminisme ; tri stable) dans tests/unit/test_import_root.py
- [x] T003 [P] [US1] Tests de `module_qualname(path, import_root)` (`src/mypkg/api.py`+`src` → `mypkg.api` ; `__init__.py` → package ; racine vide → comportement actuel) dans tests/unit/test_import_root.py
- [x] T004 [US1] `detect_import_roots(paths)` : remontée tant que le parent a un `__init__.py`, premier ancêtre sans `__init__.py` = racine d'import ; repli racine vide si ambigu — dans src/codeatlas/analyzers/python/import_root.py
- [x] T005 [US1] `module_qualname` accepte `import_root` et l'implémente ; l'analyseur calcule les racines à la construction et nomme chaque module en conséquence — dans src/codeatlas/analyzers/python/analyzer.py
- [x] T006 [P] [US1] Golden du graphe de `src-layout-demo` (modules `mypkg.*`, arêtes d'import présentes) dans tests/golden/test_src_layout_golden.py
- [x] T007 [US1] Test grandeur nature : analyse de `src/codeatlas` en layout `src/` (racine = dépôt) → arêtes d'import > 0 et couplage non nul dans tests/integration/test_src_layout_build.py per SC-001/SC-002

**Checkpoint**: US1 livrable — le graphe est juste sur les projets `src/`.

## Phase 3: User Story 2 - Package en sous-répertoire (P2)

**Goal**: racine d'import correcte quel que soit l'emplacement du package, par sous-projet.

**Independent Test**: quickstart §1 sur un package en sous-répertoire ; monorepo à `src/` par sous-projet.

- [x] T008 [P] [US2] Tests : package dans un sous-répertoire arbitraire → nom depuis sa racine d'import ; plusieurs racines indépendantes ; racine par sous-projet (monorepo) ; module orphelin → nom nu ; cas ambigu → repli — dans tests/unit/test_import_root.py
- [x] T009 [US2] Généralisation de `detect_import_roots` aux racines multiples/décalées et intégration par sous-projet (aucune hypothèse de racine commune) dans src/codeatlas/analyzers/python/import_root.py et l'appel de l'analyseur

**Checkpoint**: US1 + US2 — noms justes sur tous les agencements réels.

## Phase 4: User Story 3 - Répertoires générés ignorés (P3)

**Goal**: le site généré et les artefacts de build ne créent plus de faux modules/sous-projets.

**Independent Test**: quickstart §4 (aucun module issu d'un site généré).

- [x] T010 [P] [US3] Tests : un répertoire contenant `.codeatlas-generated` est ignoré par `discover_files` ; les nouveaux motifs par défaut excluent les artefacts sans ambiguïté ; réintégration explicite possible — dans tests/integration/test_generated_dirs_ignored.py
- [x] T011 [US3] `discover_files` ignore tout répertoire marqué `.codeatlas-generated` ; `DEFAULT_EXCLUDES` gagne les artefacts générés sans ambiguïté — dans src/codeatlas/analyzers/base.py et src/codeatlas/config.py
- [x] T012 [US3] Le builder dépose `.codeatlas-generated` (contenu statique) à la racine du site produit dans src/codeatlas/site/builder.py

## Phase 5: Polish & non-régression

- [x] T013 Non-régression : `pytest tests/golden` sans régénération (python-demo et corpus non-`src/` inchangés octet pour octet) per SC-003 ; mettre à jour le `codeatlas.toml` de dogfooding si le marqueur/exclusions le permettent
- [x] T014 Couverture ≥ 80 %, ruff + mypy propres, quickstart 005 exécuté ; dogfooding : `codeatlas serve .` depuis la racine du dépôt montre enfin un graphe connecté

---

## Dependencies

Setup (T001) → US1 (T002-T007, MVP) → US2 (T008-T009, généralise la détection) →
US3 (T010-T012, indépendante) → Polish (T013-T014). US2 étend le module de US1
(même fichier import_root.py → séquentiel). US3 touche d'autres fichiers (base.py,
config.py, builder.py) → parallélisable avec US2.

## Parallel opportunities

- T002/T003 (tests US1) en parallèle avant T004/T005.
- T006 (golden) et T007 (dogfood) en parallèle après T005.
- US3 (T010-T012) en parallèle de US2 (fichiers disjoints).

## Implementation Strategy

MVP = Phases 1-2 (US1) : corrige le cas dominant (`src/`) et le symptôme observé.
Puis US2 (généralisation), US3 (bruit des répertoires générés), Polish. Arrêt possible
au checkpoint US1 avec une valeur déjà démontrable (dogfood connecté).
