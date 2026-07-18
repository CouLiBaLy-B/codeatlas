# Tasks: Diff architectural

**Input**: Design documents from `/specs/002-architectural-diff/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUS — test-first (constitution V) : chaque test écrit et vérifié en
échec avant l'implémentation correspondante.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [x] T001 Créer le package src/codeatlas/baseline/ (`__init__.py`) ; ajouter les clés `[check]` fail_on_new_cycles / fail_on_new_violations / fail_on_removed_public_api / max_doc_coverage_drop (fail_on_new_inferred existe déjà) dans src/codeatlas/config.py ; ajouter `.codeatlas/**` aux exclusions par défaut (la baseline ne doit jamais être analysée)

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: la capture canonique est consommée par toutes les stories

- [x] T002 [P] Tests unitaires de la capture (structure attendue sur le corpus, double capture identique octet pour octet, aucun horodatage, tri des listes) dans tests/unit/test_baseline.py
- [x] T003 [P] Golden test du JSON de baseline (contrat baseline-schema.md) dans tests/golden/test_baseline_json.py
- [x] T004 Modèle Baseline (dataclasses) + capture depuis CodeGraph + insights existants dans src/codeatlas/baseline/capture.py
- [x] T005 Lecture/écriture .codeatlas/ et history/, JSON canonique, contrôle baseline_version/ir_version → erreur d'usage explicite (FR-006) dans src/codeatlas/baseline/store.py
- [x] T006 api.capture_baseline (façade bibliothèque, constitution II) dans src/codeatlas/api.py

**Checkpoint**: baseline capturable et rechargeable

---

## Phase 3: User Story 1 - Comparer l'état courant à une référence (P1)

- [x] T007 [P] [US1] Tests unitaires de la comparaison (apparu/disparu par catégorie, API modifiée appariée, is_empty, metric_deltas, déterminisme) dans tests/unit/test_arch_delta.py
- [x] T008 [US1] Moteur de comparaison Baseline × Baseline → ArchDelta dans src/codeatlas/baseline/compare.py
- [x] T009 [P] [US1] Tests d'intégration CLI des 4 scénarios d'acceptation US1 (corpus muté en tmp : cycle introduit, API supprimée ; diff vide exit 0 ; baseline absente/incompatible exit 2 ; double run identique) dans tests/integration/test_diff_cli.py
- [x] T010 [US1] Rendu console texte de l'ArchDelta + api.diff_baseline dans src/codeatlas/baseline/render.py et src/codeatlas/api.py
- [x] T011 [US1] Commandes `codeatlas baseline` (--out, --archive) et `codeatlas diff` (--baseline, --format text|json, --out) dans src/codeatlas/cli.py

**Checkpoint**: US1 livrable seule (diff local exploitable)

---

## Phase 4: User Story 2 - Gate CI sur régression (P1)

- [x] T012 [P] [US2] Tests unitaires des règles de régression (chaque règle : passe/échoue, opt-in par défaut, max_doc_coverage_drop en points) dans tests/unit/test_regression_rules.py
- [x] T013 [P] [US2] Tests d'intégration gate (exit 3 règle violée, exit 0 sans règle, baseline absente → création + exit 0 + message) dans tests/integration/test_gate_baseline.py
- [x] T014 [US2] Évaluation des règles sur l'ArchDelta → CheckResults dans src/codeatlas/insights/checks.py
- [x] T015 [US2] Extension `codeatlas check` : --against-baseline [FILE] + options de règles (contrat cli.md), rapport JSON incluant les règles dans src/codeatlas/cli.py

**Checkpoint**: US1+US2 = promesse produit tenue en CI

---

## Phase 5: User Story 3 - Commentaire de pull request (P2)

- [x] T016 [P] [US3] Golden tests du markdown PR (marqueur en 1re ligne, régressions en tête avec icônes, API modifiées appariées, diff vide explicite, troncature à 150 lignes avec compte exact) dans tests/golden/test_pr_comment.py
- [x] T017 [US3] Rendu markdown PR (`diff --format markdown`) dans src/codeatlas/baseline/render.py
- [x] T018 [US3] Action GitHub : inputs `baseline` et `pr-comment`, étape gh api create-or-update par recherche du marqueur, copie dans $GITHUB_STEP_SUMMARY, doc d'usage dans action/action.yml et action/README.md

**Checkpoint**: US3 — le diff visible en revue

---

## Phase 6: User Story 4 - Changelog architectural (P3)

- [x] T019 [P] [US4] Test d'intégration changelog (2 baselines archivées → page ordonnée par tri naturel, entrée par label avec son diff) dans tests/integration/test_changelog.py
- [x] T020 [US4] Archives labellisées + tri naturel documenté dans src/codeatlas/baseline/store.py
- [x] T021 [US4] Page changelog du site (template + builder + libellés i18n en/fr) dans src/codeatlas/site/templates/changelog.md.j2, src/codeatlas/site/builder.py, src/codeatlas/site/i18n.py

**Checkpoint**: toutes les stories livrées

---

## Phase 7: Polish

- [x] T022 Exécuter quickstart.md intégralement, corriger les écarts ; section « L'architecture sous contrôle de version » dans README.md ; vérifier couverture ≥ 80 %, ruff, mypy

---

## Dependencies & Execution Order

- Setup → Foundational → US1 → US2 (dépend du compare d'US1) → US3 (dépend du diff) →
  US4 (dépend du store) → Polish. US3 et US4 parallélisables après US1.
- Dans chaque story : tests [P] d'abord (échec vérifié), puis implémentation.

## Implementation Strategy

MVP = Phases 1–4 (US1+US2, les deux P1) ; US3/US4 en incréments indépendants.
