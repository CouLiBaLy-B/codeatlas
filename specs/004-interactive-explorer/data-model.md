# Data Model: Explorateur interactif

**Feature**: 004-interactive-explorer | **Date**: 2026-07-18

Tous les modèles dérivent exclusivement du `CodeGraph` (IR) et des insights existants
(principe III). Toutes les collections sont triées (ordre lexicographique sur les
identifiants stables) ; aucune valeur non déterministe (horodatage, aléa, chemin
absolu) n'apparaît dans les artefacts.

## ExplorerData (racine des données de vues)

Conteneur émis en `atlas-data-<vue>.js` (JSON canonique, cf. research R3).

| Champ | Type | Notes |
|---|---|---|
| `schema_version` | int | injecté à l'émission dans chaque payload (pas un champ du dataclass) |
| `graph` | GraphView | vue d'architecture (US1) |
| `search` | list[SearchEntry] | index de symboles (US2) — fichier séparé |
| `dashboard` | DashboardData | métriques + treemap (US4) — fichier séparé |

## GraphView

Graphe multi-niveaux avec positions précalculées (research R1/R2).

| Champ | Type | Notes |
|---|---|---|
| `levels` | list[str] | ordre de dépliage : `["subproject", "package", "module"]` |
| `nodes` | list[GraphNode] | triés par `id` |
| `edges` | list[GraphEdge] | triés par (`source`, `target`, `kind`) |

**GraphNode**: `id` (str — id IR pour les modules, `pkg:<sub>/<package>` et
`sub:<id>` pour les conteneurs), `label`, `level` (`subproject|package|module`),
`parent` (id du conteneur ou null), `language`, `layer` (couche détectée, filtre),
`subproject`, `metrics` (modules : loc/complexity/doc_coverage/fan_in/fan_out ;
conteneurs : loc/modules), `pos` {x: int, y: int} (layout précalculé ;
conteneurs : barycentre des enfants), `page` (fiche, vide pour les conteneurs),
`degraded` (bool — sous-projet porteur de fichiers ignorés).

**GraphEdge**: `source`, `target`, `kind` (`import` entre modules, `service`
entre sous-projets ; le containment passe par `parent`), `certain` (bool — faux
dès qu'un lien agrégé est inféré), `weight` (int, nombre de liens agrégés).

**Règles de validation**
- `parent` référence un nœud de niveau strictement supérieur ; pas de cycle de
  containment.
- Toute arête agrégée a `weight ≥ 1` ; les arêtes de niveau N ne relient que des
  nœuds de niveau N.
- Tout `page` pointe vers une page réellement émise par le site (vérifié au build).

## SearchEntry

| Champ | Type | Notes |
|---|---|---|
| `name` | str | nom court du symbole |
| `qualname` | str | nom qualifié unique (désambiguïse les homonymes) |
| `kind` | str | `module|class|function|method` |
| `signature` | str | vide pour les modules |
| `module` | str | module d'origine |
| `language` | str | |
| `page` | str | cible de navigation (fiche + ancre) |

Tri : (`name`, `qualname`) — le classement de pertinence est fait côté client selon
FR-007 ; l'index lui-même reste canonique.

## SymbolCard (fiche — rendu statique, pas un artefact JSON)

Modèle passé aux templates de fiches (module et symbole) :
`identity` (nom, kind, langage, couche, sous-projet), `metrics` (dict trié),
`inbound` / `outbound` (listes de références {id, label, kind, certain, page}),
`source` (SourceExcerpt | null), `warnings` (list[AnalysisWarning]).

**SourceExcerpt**: `path` (relatif au dépôt), `start_line`, `end_line`, `code`
(texte exact des lignes) — omis si `include_source = false` ou fichier illisible
(la fiche l'indique alors explicitement, FR/edge case).

## DashboardData

| Champ | Type | Notes |
|---|---|---|
| `rows` | list[DashboardRow] | une par module, triées par `id` |
| `treemap` | Treemap | layout précalculé (research R7) |
| `warnings` | list[AnalysisWarning] | fichiers ignorés + motifs (FR-015) |

**DashboardRow**: `id`, `label`, `page`, `language`, `layer`, `subproject`,
`metrics` (dict trié — mêmes clés pour toutes les lignes, valeur null si non
applicable).

**Treemap**: `metric` (métrique demandée), `fallback` (`"loc"` si la métrique
est nulle partout, sinon vide), `omitted` (modules à valeur nulle, jamais de
cellule invisible), `cells` : list de {`id`, `label`, `page`, `x`, `y`, `w`,
`h`, `value`} — rectangles entiers aux bords partagés (ni trou ni
chevauchement), ordre déterministe, rendus en SVG cliquable au build.

**AnalysisWarning** (réutilise le modèle existant du rapport) : `path`, `reason`,
`scope`.

## WorkshopSession (mode atelier — état en mémoire, jamais sérialisé)

| Champ | Type | Notes |
|---|---|---|
| `root` | Path | dépôt surveillé |
| `graph` | CodeGraph | IR courante, mise à jour incrémentalement |
| `file_index` | dict[path → set[element_id]] | provenance, dérivé de l'IR |
| `pending` | set[path] | événements regroupés (debounce) en attente |
| `build_token` | str | compteur monotone de génération, exposé sur `/__atlas_build__` (jamais écrit dans les artefacts) |
| `warnings` | list[AnalysisWarning] | état courant, reflété dans le site servi |

**Transitions**
1. `idle` —événement fichier→ `pending` (accumulation pendant la fenêtre de debounce)
2. `pending` —fenêtre échue→ `rebuilding` : invalidation (R6) → réanalyse partielle →
   fusion IR → réémission ciblée → incrément de `build_token` → `idle`
3. Erreur d'analyse pendant `rebuilding` → l'élément passe en `warnings`, la session
   revient à `idle` (jamais d'arrêt, principe IV)
4. Suppression/renommage → retrait des éléments du graphe + réémission des dépendants

**Invariant de convergence** : à code source identique, l'état servi après N cycles
incrémentaux est identique octet pour octet à un build complet à froid (testé).
