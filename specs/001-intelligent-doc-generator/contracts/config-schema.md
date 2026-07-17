# Contract: Configuration `codeatlas.toml`

Configuration **optionnelle** (FR-016 : zéro config obligatoire). Résolution :
`--config FILE` > `codeatlas.toml` à la racine analysée > `[tool.codeatlas]` dans
`pyproject.toml` > défauts intégrés. TOML uniquement (tomllib, Python 3.11+).

## Schéma complet (avec les défauts)

```toml
[project]
title = ""            # défaut : nom du répertoire racine
language = "en"       # langue des libellés du site généré : "en" | "fr" (extensible).
                      # Ne traduit PAS le contenu extrait (docstrings, noms de symboles).

[analysis]
include_private = false
exclude = []          # motifs glob AJOUTÉS aux exclusions par défaut
languages = []        # vide = tous les langages disponibles ; sinon filtre

[graphs]
call_depth = 3        # profondeur des graphes d'appels (build et diagram --type calls)
focus_depth = 1       # profondeur des diagrammes focalisés (diagram --type class)
                      # Précédence : option CLI --depth > ces clés > défauts ci-dessus.

[metrics]
complexity_warn = 10
complexity_critical = 20
doc_coverage_warn = 60    # % en dessous duquel un module passe "warn"

[site]
enabled = true
out = "codeatlas-docs"
extra_nav = []        # pages manuelles : échafaudées au 1er build, JAMAIS écrasées ensuite
svg_export = false    # réservé — non supporté v1 (avertissement svg-unavailable, jamais silencieux)

[check]               # seuils du mode CI `codeatlas check` (FR-018)
max_package_cycles = -1      # -1 = non vérifié
min_doc_coverage = -1
max_critical_symbols = -1
fail_on_new_inferred = false # réservé v2 (comparaison entre exécutions)

[monorepo]
detect = true
roots = []            # forcer des racines de sous-projets (surcharge la détection)
```

## Exclusions par défaut (non configurables autrement que par ajout)

```text
**/node_modules/**   **/.venv/**  **/venv/**   **/__pycache__/**
**/dist/**           **/build/**  **/target/** **/.git/**
**/*.min.js          **/vendor/** **/.*/**     (dossiers cachés)
```

## Règles de validation

- Clé inconnue → erreur d'usage (exit 2) avec suggestion de la clé la plus proche —
  jamais d'ignorance silencieuse.
- Valeurs hors domaine (profondeur < 1, pourcentage hors [0,100]) → exit 2, message
  explicite.
- Les options CLI priment sur le fichier ; le fichier prime sur les défauts.
- La config effective (fusionnée) est rappelée dans l'AnalysisReport (`--verbose`).
