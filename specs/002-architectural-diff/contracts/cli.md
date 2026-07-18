# Contract: CLI du diff architectural

Extension du contrat CLI de la feature 001 — mêmes conventions (exit codes 0/1/2/3,
stdout = données, stderr = messages, CLI façade de `codeatlas.api`).

## `codeatlas baseline PATH`

Capture l'état architectural courant.

| Option | Défaut | Description |
| --- | --- | --- |
| `--out FILE` | `<PATH>/.codeatlas/baseline.json` | destination |
| `--archive LABEL` | — | copie aussi vers `.codeatlas/history/<LABEL>.json` |
| `--config, -c FILE` | auto | configuration habituelle |

Exit : 0 (capture) ; 1 (analyse impossible) ; 2 (usage). Ré-exécution sur état
identique → fichier identique octet pour octet.

## `codeatlas diff PATH`

Compare l'état courant à la baseline. **Toujours informatif : exit 0** (le blocage est
le rôle de `check`).

| Option | Défaut | Description |
| --- | --- | --- |
| `--baseline FILE` | `<PATH>/.codeatlas/baseline.json` | référence |
| `--format` | `text` | `text` (console) \| `markdown` (commentaire PR) \| `json` |
| `--out FILE` | stdout | destination du rendu |

Baseline absente → exit 2 avec message (« lancez `codeatlas baseline` ») ; version
incompatible → exit 2 (FR-006).

## `codeatlas check PATH` (extensions)

| Option | Clé `[check]` | Sémantique |
| --- | --- | --- |
| `--against-baseline [FILE]` | — | active l'évaluation des règles de régression |
| `--fail-on-new-cycles` | `fail_on_new_cycles = false` | nouveau cycle interdit |
| `--fail-on-new-violations` | `fail_on_new_violations = false` | nouvelle violation interdite |
| `--fail-on-new-inferred` | `fail_on_new_inferred = false` | nouveau lien incertain interdit |
| `--fail-on-removed-public-api` | `fail_on_removed_public_api = false` | suppression d'API interdite |
| `--max-doc-coverage-drop N` | `max_doc_coverage_drop = -1` | chute max en points de % |

Comportements : baseline absente → **création + exit 0** + message explicite (FR-005) ;
règle violée → exit 3, règles nommées dans la sortie et le rapport JSON (`checks`).

## Markdown « commentaire de PR » (`diff --format markdown`)

1. Première ligne : marqueur stable `<!-- codeatlas:arch-diff -->` (idempotence).
2. Résumé chiffré (1 ligne par catégorie changée), régressions potentielles en tête
   avec 🔴/⚠️, évolutions neutres ensuite.
3. Détails par catégorie : listes apparu/disparu, API modifiées appariées
   (ancienne → nouvelle signature).
4. Diff vide → « ✅ Aucun changement architectural ».
5. Troncature au-delà de 150 lignes de contenu : compte exact + mention explicite.

## Action GitHub (nouveaux inputs)

| Input | Défaut | Description |
| --- | --- | --- |
| `baseline` | `""` | chemin de baseline ; non vide → exécute `check --against-baseline` |
| `pr-comment` | `false` | poste/met à jour le commentaire de PR (recherche du marqueur via l'API GitHub) et copie le markdown dans le job summary |

La publication réseau vit exclusivement dans l'Action (contexte CI) — le cœur ne
produit que le markdown.
