# Contract: CLI `codeatlas`

La CLI est une façade fine au-dessus de l'API bibliothèque (`codeatlas.api`) —
constitution II. Exécution toujours non interactive (FR-018).

## Commandes

### `codeatlas build PATH`

Génère le site complet + artefacts intermédiaires.

| Option | Défaut | Description |
| --- | --- | --- |
| `--out, -o DIR` | `./codeatlas-docs` | répertoire de sortie (site + artefacts) |
| `--config, -c FILE` | auto-détection | `codeatlas.toml` ou `[tool.codeatlas]` |
| `--exclude PATTERN` | (répétable) | motifs glob en plus des exclusions par défaut |
| `--include-private` | faux | inclut les symboles privés |
| `--depth N` | 3 | profondeur des graphes d'appels |
| `--site / --no-site` | `--site` | `--no-site` : artefacts .md/.mmd seuls (FR-014) |
| `--svg` | faux | exporte aussi les diagrammes en SVG (extra `[svg]`) |
| `--json-report FILE` | — | écrit l'AnalysisReport en JSON |
| `--quiet / --verbose` | normal | verbosité console (Rich) |

### `codeatlas check PATH`

Mode CI (FR-018) : analyse sans générer le site, évalue les seuils, échoue si
régression.

| Option | Défaut | Description |
| --- | --- | --- |
| `--config, -c FILE` | auto-détection | seuils lus dans `[check]` de la config |
| `--max-package-cycles N` | — | échec si cycles de packages > N |
| `--min-doc-coverage PCT` | — | échec si couverture docstrings < PCT |
| `--max-critical-symbols N` | — | échec si symboles `critical` (complexité) > N |
| `--json-report FILE` | — | rapport machine |

### `codeatlas diagram PATH`

Diagramme focalisé (FR-010), écrit sur stdout ou `--out`.

| Option | Défaut | Description |
| --- | --- | --- |
| `--type` | `class` | `class` \| `deps` \| `calls` |
| `--focus SYMBOL` | requis pour `class`/`calls` | nom qualifié ou nom court non ambigu |
| `--depth N` | `[graphs].focus_depth` (`class`) / `[graphs].call_depth` (`calls`) | rayon autour du symbole ; l'option CLI prime sur la config |
| `--out FILE` | stdout | fichier .mmd |

## Exit codes

| Code | Signification |
| --- | --- |
| 0 | succès (avertissements possibles — tolérance, constitution IV) |
| 1 | erreur fatale : aucun fichier analysable, sortie inaccessible, erreur interne |
| 2 | erreur d'usage : arguments/config invalides |
| 3 | `check` : au moins un seuil violé |

Les fichiers non parsables ne changent **jamais** le code de sortie de `build`
(constitution IV) ; ils apparaissent dans le rapport et la doc.

## AnalysisReport JSON (`--json-report`)

Schéma stable (versionné `report_version`), clés triées, pas d'horodatage :

```json
{
  "report_version": 1,
  "root": "chemin/relatif",
  "subprojects": [{"id": "…", "language": "python", "files_analyzed": 42}],
  "counts": {
    "files_analyzed": 42,
    "files_skipped": 1,
    "nodes": 310,
    "edges_certain": 512,
    "edges_inferred": 34
  },
  "skipped": [{"path": "pkg/bad.py", "reason": "SyntaxError: line 3"}],
  "warnings": [{"code": "unresolved-call", "where": "pkg.mod.f", "detail": "…"}],
  "checks": [{"name": "min-doc-coverage", "threshold": 80, "actual": 72, "passed": false}],
  "duration_seconds": 1.8
}
```

`duration_seconds` est le seul champ non déterministe : il est exclu des comparaisons
golden et absent des artefacts du site.

## Garanties transverses

- Aucune écriture hors du répertoire `--out` (+ fichier `--json-report`).
- Ré-exécution : le contenu de `--out` est remplacé de façon atomique ; les pages
  manuelles référencées dans la config (`site.extra_nav`) ne sont jamais écrasées.
- Sortie stdout/stderr : messages humains sur stderr, données machine (diagram, json)
  sur stdout — scriptable.
