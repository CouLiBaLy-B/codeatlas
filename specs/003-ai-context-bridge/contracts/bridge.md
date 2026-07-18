# Contract: Pont IA — CLI et outils MCP

Conventions inchangées : exit 0/1/2, stdout = données, stderr = messages,
CLI/serveur = façades de `codeatlas.api`.

## `codeatlas export PATH`

| Option | Défaut | Description |
| --- | --- | --- |
| `--format` | `repomap` | `repomap` (markdown à budget) \| `graph` (JSON canonique de l'IR) |
| `--budget N` | `[export].budget` (24000) | taille max en caractères (repomap) |
| `--out FILE` | stdout | destination (`.codeatlas/repomap.md` conseillé pour committer) |
| `--config, -c` | auto | configuration habituelle |

Garanties : déterministe octet pour octet ; priorisation documentée (modules à
points d'entrée, puis fan-in décroissant, puis alpha ; module entier ou rien) ;
section finale « Omis (budget) » si coupe ; budget < en-tête minimal → erreur
d'usage explicite (exit 2).

## `codeatlas impact PATH --focus SYMBOLE|FICHIER`

| Option | Défaut | Description |
| --- | --- | --- |
| `--focus` | requis | nom qualifié, nom court non ambigu, ou chemin de fichier analysé |
| `--depth N` | `[graphs].call_depth` | niveaux de propagation inverse |
| `--format` | `text` | `text` \| `json` |

Sortie : niveaux 1..N (appelants/importeurs directs puis indirects), liens
incertains marqués, points d'entrée atteints signalés ; cible sans référence →
« aucun impact entrant » explicite. Ambigu/introuvable → exit 2 avec candidats.

## `codeatlas mcp PATH`

Serveur MCP **stdio** (extra `codeatlas-doc[mcp]` requis — absent → exit 2 avec la
commande d'installation). Analyse au démarrage ; aucune socket réseau.

### Outils exposés

| Outil | Entrée | Sortie (JSON, bornée) |
| --- | --- | --- |
| `overview` | — | dépôt, sous-projets, couches, points d'entrée, métriques |
| `search_symbol` | `query: str` | ≤ 25 correspondances {id, kind, file, line, signature, doc} + indicateur de troncature |
| `module_api` | `module: str` | API publique du module (classes, fonctions, signatures, docs) |
| `callers` / `callees` | `symbol: str`, `depth: int = 1` | liens avec `certainty` |
| `impact` | `target: str`, `depth: int = 3` | ImpactReport (niveaux, points d'entrée atteints) |
| `dead_code` | — | candidats {id, confidence, reason} |
| `reload` | — | ré-analyse le dépôt, renvoie les compteurs |

Règles : réponses issues du graphe uniquement (liste vide plutôt qu'invention) ;
symbole ambigu → liste des candidats ; erreurs outillées, jamais de crash serveur.

## Config

```toml
[export]
budget = 24000   # caractères ; ≥ 2000
```
