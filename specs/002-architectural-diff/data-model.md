# Data Model: Diff architectural

**Date**: 2026-07-18 | **Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Baseline

Résumé architectural versionnable, dérivé du CodeGraph + insights. Champs :

| Champ | Type | Règles |
| --- | --- | --- |
| `baseline_version` | int | version du format (1) ; incompatible → erreur d'usage |
| `ir_version` | int | version de l'IR productrice |
| `root` | str | nom du dépôt (relatif, jamais absolu) |
| `public_api` | liste triée de {id, kind, signature} | symboles publics (classes, fonctions, méthodes) |
| `package_cycles` | liste triée de listes triées | cycles de packages |
| `layer_violations` | liste triée de {source, target} | violations de couches |
| `inferred_calls` | liste triée de {source, target} | liens d'appel incertains |
| `dead_code` | liste triée de {id, confidence} | code probablement mort |
| `service_deps` | liste triée de {source, target} | liens inter-services |
| `subprojects` | liste triée de {id, language} | sous-projets |
| `skipped` | liste triée de {path, reason} | fichiers non analysés |
| `metrics` | {doc_coverage, critical_symbols, files_analyzed, nodes, edges} | entiers |

**Invariants** : JSON canonique (clés triées, UTF-8, fin `\n`), aucun horodatage,
déterministe octet pour octet à état de dépôt identique.

## ArchDelta

Résultat de `compare(old, new)` :

| Champ | Type | Règles |
| --- | --- | --- |
| `categories` | mapping catégorie → {appeared: [...], disappeared: [...]} | entrées traçables, listes triées |
| `modified_api` | liste de {id, old_signature, new_signature} | id présent des deux côtés, signature différente (appariement rendu) |
| `metric_deltas` | mapping nom → {old, new, delta} | uniquement les métriques qui changent |
| `is_empty` | bool | vrai ssi aucune catégorie ni métrique ne change |

Catégories : `public_api`, `package_cycles`, `layer_violations`, `inferred_calls`,
`dead_code`, `service_deps`, `subprojects`, `skipped`.

## RegressionRule / évaluation du gate

Réutilise `CheckResult` existant. Règles (clés `[check]`, opt-in, défaut désactivé) :

| Clé | Sémantique |
| --- | --- |
| `fail_on_new_cycles` | échec si `package_cycles.appeared` non vide |
| `fail_on_new_violations` | échec si `layer_violations.appeared` non vide |
| `fail_on_new_inferred` | échec si `inferred_calls.appeared` non vide (clé v1 réservée, rendue effective) |
| `fail_on_removed_public_api` | échec si `public_api.disappeared` non vide |
| `max_doc_coverage_drop` | échec si la couverture chute de plus de N points (−1 = désactivé) |

## Cycle de vie

```text
analyze → capture (Baseline) → store (.codeatlas/baseline.json | history/<label>.json)
analyze → capture (courant) ×  load (baseline) → compare (ArchDelta)
    → render (console | markdown PR | json)
    → evaluate rules (CheckResults, exit 3 si violation)
site : history/*.json → page changelog (diffs successifs, tri naturel des labels)
```
