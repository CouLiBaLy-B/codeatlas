# Research: Diff architectural

**Date**: 2026-07-18 | **Feature**: [spec.md](spec.md)

## R1. Format et emplacement de la baseline

**Décision**: fichier JSON canonique versionnable `.codeatlas/baseline.json` (clés
triées, UTF-8, sans horodatage), contenant un **résumé architectural dérivé** du
graphe — pas l'IR complet : APIs publiques (id, kind, signature), cycles de packages,
violations de couches, liens `inferred`, code mort (id, confiance), dépendances
inter-services, métriques globales (couverture doc, symboles critiques, compteurs),
plus `baseline_version` et la version d'IR productrice.

**Rationale**: un résumé est petit (quelques Ko), lisible en revue git, stable ; il
couvre exactement les catégories du diff. L'IR complet serait volumineux et bruité.

**Alternatives considérées**: IR complet sérialisé — rejeté (taille, bruit de diff
git) ; base SQLite — rejetée (non diffable en revue, non versionnable proprement).

## R2. Moteur de comparaison

**Décision**: comparaison ensembliste sur identifiants stables (noms qualifiés,
tuples normalisés triés) par catégorie → listes `appeared` / `disappeared`. Une API
présente des deux côtés avec une **signature différente** apparaît dans les deux
listes ; le rendu l'affiche appariée comme « modifiée ». Pas de détection de
renommage (assumé par la spec : disparition + apparition).

**Rationale**: trivial à rendre déterministe, comportement prévisible, conforme
FR-002/FR-003.

**Alternatives considérées**: rapprochement heuristique des renommages (similarité) —
rejeté v1 : non déterministe dans les cas limites, contraire à l'honnêteté du produit.

## R3. Surface CLI et configuration

**Décision**:
- `codeatlas baseline PATH [--out FILE] [--archive LABEL]` — capture (défaut :
  `.codeatlas/baseline.json` dans le dépôt analysé) ; `--archive` copie aussi vers
  `.codeatlas/history/<label>.json` (changelog).
- `codeatlas diff PATH [--baseline FILE] [--format text|markdown|json]` — toujours
  exit 0 (informatif) ; markdown = format « commentaire de PR ».
- Gate : options de `codeatlas check` + section `[check]` étendue :
  `fail_on_new_cycles`, `fail_on_new_violations`, `fail_on_new_inferred` (la clé
  réservée v1 devient effective), `fail_on_removed_public_api`,
  `max_doc_coverage_drop` (points de %). Baseline requise : absente → création +
  exit 0 + message (FR-005). Violation → exit 3 (code de gate existant).

**Rationale**: réutilise les conventions établies (exit codes, config TOML stricte,
CLI façade de `codeatlas.api`) ; « code dédié » de la spec = exit 3, déjà distinct de
0/1/2.

**Alternatives considérées**: commande `codeatlas gate` séparée — rejetée : `check`
est déjà le mode CI, une seule porte d'entrée.

## R4. Commentaire de pull request

**Décision**: le cœur produit le markdown (`diff --format markdown`) avec un marqueur
HTML stable `<!-- codeatlas:arch-diff -->` en première ligne ; régressions en tête
avec icônes, sections apparu/disparu par catégorie, troncature explicite au-delà de
150 lignes de contenu. La **publication** est faite par l'Action GitHub (nouvel input
`pr-comment: true`) via l'API GitHub (`gh api`) : recherche du commentaire portant le
marqueur → mise à jour, sinon création. Le cœur reste hors-ligne.

**Rationale**: séparation stricte conforme constitution I (le réseau n'existe que
dans le contexte CI, hors du cœur) ; le marqueur garantit l'idempotence (FR-007).

**Alternatives considérées**: publication par le cœur Python — rejetée
(constitution I) ; commentaire par job summary GitHub uniquement — rejeté : moins
visible en revue, mais le markdown est AUSSI écrit dans `$GITHUB_STEP_SUMMARY`.

## R5. Changelog architectural

**Décision**: page `changelog.md` du site générée quand `.codeatlas/history/` contient
des baselines archivées : une entrée par label, ordonnée par tri naturel documenté
(segments numériques comparés numériquement), chaque entrée montrant le diff avec la
baseline précédente.

**Rationale**: dérivé entièrement d'artefacts versionnés, déterministe, zéro état
caché.

**Alternatives considérées**: historique via git (comparer des révisions) — rejeté
v1 : dépendance à git et aux checkouts, non déterministe hors dépôt git.

## R6. Performance et réutilisation

**Décision**: `baseline` et `diff` réutilisent `api.analyze` + les insights existants
(cycles, architecture, code mort, métriques) ; la comparaison est O(n log n) sur les
résumés. Aucune nouvelle dépendance.

**Rationale**: SC-003 (< 10 s hors site) tient : l'analyse de 50 k lignes ≈ 9 s, le
résumé et le diff sont négligeables.
