# Contracts: Explorateur interactif

**Feature**: 004-interactive-explorer | **Date**: 2026-07-18

Trois surfaces : API de bibliothèque (source de vérité, principe II), CLI (façade),
et le contrat données ↔ navigateur (schéma des artefacts embarqués).

## 1. API de bibliothèque (`codeatlas.api`)

```python
def build_explorer_data(graph: CodeGraph, config: Config | None = None) -> ExplorerData:
    """Construit toutes les données des vues interactives (graphe multi-niveaux
    avec positions, index de recherche, tableau de bord + treemap).
    Pur et déterministe : mêmes entrées → même objet. Ne consomme que l'IR et
    les insights (constitution III)."""

def serve_docs(
    path: Path,
    config: Config | None = None,
    *,
    port: int = 8321,
    watch: bool = True,
    open_browser: bool = False,
    on_event: Callable[[dict], None] | None = None,
    workdir: Path | None = None,
) -> WorkshopSession:
    """Démarre le mode atelier : build initial, surveillance des sources,
    régénération incrémentale (granularité : unité de sous-projet), service HTTP
    local — bind 127.0.0.1 codé en dur. Lève PortInUseError si le port est
    occupé. `session.stop()` arrête proprement (idempotent)."""
```

- `codeatlas.explorer.emit.write_data(data, docs_dir) -> list[Path]` émet
  `assets/data/atlas-*.js` en JSON canonique et retourne les chemins triés ; la
  treemap est rendue en SVG inline dans la page Santé (lisible sans JS).
- `build_site` existant appelle `build_explorer_data` quand `[explorer].enabled` ;
  la doc gagne les vues interactives par défaut, `--no-explorer` restitue le site
  de la feature 001.
- Fiches enrichies : `render_module_page(..., explorer=, source_root=, relations=)`
  avec `build_relations_index(graph)` précalculé une fois par build (performance).
- Erreurs : `PortInUseError(port)` (dans `codeatlas.serve.server`, hérite de
  `CodeAtlasError`) ; les échecs d'analyse en session ne lèvent jamais — ils
  alimentent `warnings` (principe IV) ; `serve_docs` lève `CodeAtlasError` si
  rien n'est analysable au premier build ou si l'extra `[site]` manque.

## 2. CLI

### `codeatlas serve [PATH]` (nouvelle commande)

| Option | Défaut | Effet |
| --- | --- | --- |
| `--port INT` | `8321` | port d'écoute (127.0.0.1 uniquement, non configurable) |
| `--open` | off | ouvre le navigateur au démarrage |
| `--watch / --no-watch` | `--watch` | `--no-watch` : sert le site sans surveillance |
| `--json` | off | événements de session en JSON Lines sur stdout (build, reload, warning) |

Codes retour : `0` arrêt propre (Ctrl-C ou SIGTERM) ; `1` erreur fatale, dont
« aucun fichier analysable » (cohérent avec `build`) ; `2` erreur d'usage
(chemin invalide, config invalide) ; `4` port occupé (message clair, pas de
traceback).

Sortie `--json` (une ligne par événement, clés triées) :

```json
{"event": "build", "trigger": "initial", "elements": 128, "warnings": 2, "duration_ms": 1840}
{"event": "reload", "trigger": "src/pkg/mod.py", "elements": 3, "warnings": 2, "duration_ms": 310}
{"event": "warning", "path": "src/pkg/bad.py", "reason": "syntax-error", "scope": "file"}
```

### `codeatlas build` (étendu, rétro-compatible)

- Émet en plus : `assets/cytoscape.min.js` (vendor épinglé), `assets/atlas-*.js`
  (JS maison), `assets/data/atlas-*.js` (données), treemap SVG inline (page
  Santé), fiches enrichies. Aucun changement des sorties existantes hors ajout.
- `--no-explorer` : désactive les vues interactives (site strictement équivalent à
  la feature 001).

### Configuration (`codeatlas.toml`)

```toml
[explorer]
enabled = true          # false ≡ --no-explorer
include_source = true   # extraits de source sur les fiches
default_metric = "complexity"  # métrique initiale de la treemap
```

## 3. Contrat données ↔ navigateur

- Fichiers émis dans `site/assets/data/` : `atlas-graph.js`, `atlas-search.js`,
  `atlas-dashboard.js`. Chacun affecte une clé de `window.__ATLAS__` et porte
  `schema_version` (entier, incrémenté à tout changement incompatible ; le JS
  embarqué refuse poliment un schéma inconnu → repli statique).
- Schémas : voir [data-model.md](../data-model.md) — GraphView, SearchEntry,
  DashboardData. JSON canonique : clés triées, listes triées comme spécifié,
  `ensure_ascii = false`, séparateurs `", "`/`": "` fixes, LF final unique.
- Le JS maison (`atlas-explorer.js`, `atlas-search.js`, `atlas-tables.js`) ne fait
  **aucune requête réseau** ; seule exception, en mode atelier uniquement : polling
  de `GET /__atlas_build__` (réponse : jeton texte brut) injecté par le serveur,
  jamais présent dans les artefacts sur disque.
- État des filtres de l'explorateur encodé dans `location.hash`
  (`#lang=python&layer=domain&sub=api`) — partageable, fonctionne en `file://`.
- Vendor : `cytoscape.min.js` version épinglée, empreinte SHA-256 enregistrée et
  vérifiée par un test.

## 4. Endpoints du mode atelier (localhost uniquement)

| Route | Réponse | Notes |
| --- | --- | --- |
| `GET /**` | fichiers du site généré | statique, types MIME corrects |
| `GET /__atlas_build__` | jeton de build (texte) | poll léger pour l'auto-reload |
| `GET /__atlas_reload__.js` | script de polling | injecté dans le HTML servi, jamais sur disque |

Aucune autre route ; aucune écriture via HTTP ; bind `127.0.0.1` codé en dur.
