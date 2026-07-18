# Implementation Plan: Diff architectural

**Branch**: `002-architectural-diff` | **Date**: 2026-07-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-architectural-diff/spec.md`

## Summary

Rendre l'architecture diffable : capture d'une **baseline** (résumé architectural JSON
canonique versionnable), **comparaison** ensembliste par catégories (apparu/disparu,
traçable), **gate CI** par règles opt-in dans `[check]`, **commentaire de PR**
idempotent produit par le cœur et publié par l'Action, **changelog** de site depuis
les baselines archivées. Tout dérive du graphe et des insights existants — aucune
nouvelle dépendance.

## Technical Context

**Language/Version**: Python ≥ 3.11 (inchangé)

**Primary Dependencies**: aucune nouvelle — réutilise `api.analyze`, insights
(graph/metrics/architecture/deadcode), config TOML stricte, renderers markdown.

**Storage**: fichiers versionnables — `.codeatlas/baseline.json`,
`.codeatlas/history/<label>.json`.

**Testing**: pytest, mêmes disciplines : test-first, golden files pour le markdown de
PR et le JSON de baseline, corpus python-demo muté en tmp pour les scénarios
apparu/disparu, double-run octet pour octet.

**Target Platform / Project Type**: inchangés (bibliothèque + CLI, multiplateforme).

**Performance Goals**: SC-003 — baseline + diff + gate < 10 s sur 50 k lignes (hors
site) ; comparaison O(n log n) sur résumés.

**Constraints**: constitution I–V ; baseline sans horodatage ; publication réseau
confinée à l'Action (contexte CI) ; clé config inconnue = erreur (conventions
existantes).

**Scale/Scope**: 4 user stories ; baseline de quelques Ko ; troncature d'affichage
explicite à 150 lignes de contenu PR.

## Constitution Check

| # | Principe | Évaluation | Verdict |
| --- | --- | --- | --- |
| I | Déterminisme, hors-ligne | Baseline/diff canoniques sans horodatage ; publication PR déléguée à l'Action (CI), le cœur n'ouvre aucune socket | ✅ |
| II | Bibliothèque d'abord | `api.capture_baseline`, `api.diff_baseline` ; CLI façade | ✅ |
| III | IR unique | Le résumé de baseline est dérivé du CodeGraph + insights, aucun accès analyseur | ✅ |
| IV | Tolérance | Les `skipped` font partie du résumé ; baseline absente → création, jamais d'échec | ✅ |
| V | Test-first, ≥ 80 % | Tests et goldens avant implémentation, corpus mutés | ✅ |

**Re-check post-Phase 1** : ✅ — aucune violation, pas d'entrée en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-architectural-diff/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── baseline-schema.md    # schéma JSON de la baseline + règles de canonicité
│   └── cli.md                # commandes baseline/diff, extensions de check, markdown PR
└── tasks.md                  # (/speckit-tasks)
```

### Source Code (repository root)

```text
src/codeatlas/
├── baseline/
│   ├── __init__.py
│   ├── capture.py       # CodeGraph + insights → Baseline (résumé canonique)
│   ├── compare.py       # Baseline × Baseline → ArchDelta (apparu/disparu par catégorie)
│   ├── render.py        # ArchDelta → texte console / markdown PR (marqueur, troncature)
│   └── store.py         # lecture/écriture .codeatlas/, history/, contrôle de version
├── insights/checks.py   # + règles de régression (évaluation de l'ArchDelta)
├── api.py               # + capture_baseline / diff_baseline
├── cli.py               # + commandes baseline, diff ; options check --against-baseline…
├── config.py            # + clés [check] fail_on_new_* / max_doc_coverage_drop
└── site/
    ├── templates/changelog.md.j2
    └── builder.py       # + page changelog si history/ non vide

action/action.yml        # + inputs pr-comment / baseline ; étape gh api (create-or-update)
tests/
├── unit/test_baseline.py, test_arch_delta.py, test_regression_rules.py
├── golden/test_baseline_json.py, test_pr_comment.py (+ data/)
└── integration/test_diff_cli.py, test_gate_baseline.py, test_changelog.py
```

**Structure Decision**: nouveau package `baseline/` au même niveau que `insights/` —
il consomme insights + IR et produit des artefacts, comme `site/`. Aucune
modification des analyseurs.

## Complexity Tracking

Aucune violation constitutionnelle — section vide.
