# Implementation Plan: Pont IA

**Branch**: `003-ai-context-bridge` | **Date**: 2026-07-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-ai-context-bridge/spec.md`

## Summary

Produire le substrat déterministe que consomment les assistants IA : **carte du
dépôt** markdown à budget (`codeatlas export`), **serveur MCP local** en extra
(`codeatlas mcp`, outils purs sur le graphe), **analyse d'impact** par niveaux
(`codeatlas impact`, aussi outil MCP), **parcours de lecture** structurel (carte +
site). Zéro LLM, zéro réseau sortant, zéro contenu inventé.

## Technical Context

**Language/Version**: Python ≥ 3.11 (inchangé). **Primary Dependencies**: cœur
inchangé ; extra `[mcp]` = SDK officiel `mcp` (FastMCP, stdio). **Storage**: stdout /
fichiers (`.codeatlas/repomap.md` conseillé, déjà exclu). **Testing**: pytest,
test-first, goldens (repomap), corpus existants ; outils MCP testés comme fonctions
pures, serveur en smoke (skip si extra absent). **Performance**: SC-003 — réponse
outil < 1 s sur 50 k lignes (index précalculés au chargement). **Constraints**:
constitution I–V ; budget en caractères ; omissions explicites ; réponses bornées.

## Data Model (résumé)

- **RepoMap** : sections ordonnées (en-tête, points d'entrée, parcours, API par
  module), `budget`, `omitted: [module…]` — rendu markdown déterministe.
- **ImpactReport** : `target`, `levels: [depth → ids triés]`,
  `entrypoints_reached`, `uncertain: bool par lien` (via arêtes).
- **ReadingTour** : étapes ordonnées `{module, reason, page}`.
- **Outil MCP** : entrée simple (str/int), sortie JSON-compatible bornée.

## Constitution Check

| # | Principe | Évaluation | Verdict |
| --- | --- | --- | --- |
| I | Déterminisme, hors-ligne | exports canoniques sans horodatage ; MCP en stdio (aucune socket sortante) ; résumés = doc existante uniquement | ✅ |
| II | Bibliothèque d'abord | logique dans `bridge/` + `insights/` en fonctions pures ; CLI et serveur = façades | ✅ |
| III | IR unique | tout dérive du CodeGraph + insights | ✅ |
| IV | Tolérance | budget trop petit → omissions explicites ; symbole ambigu → candidats listés | ✅ |
| V | Test-first ≥ 80 % | tests/goldens avant implémentation | ✅ |

**Re-check post-design** : ✅.

## Project Structure

```text
src/codeatlas/
├── bridge/
│   ├── __init__.py
│   ├── repomap.py       # RepoMap : priorisation, budget, rendu markdown
│   ├── tools.py         # fonctions pures des outils (search/module_api/callers/…)
│   └── server.py        # habillage FastMCP (import paresseux, extra [mcp])
├── insights/impact.py   # BFS inverse par niveaux (calls + imports)
├── insights/tour.py     # parcours de lecture structurel
├── api.py               # + export_repomap / compute_impact / reading_tour
├── cli.py               # + commandes export / impact / mcp
├── config.py            # + [export] budget
└── site/ (templates/tour.md.j2, builder, i18n)

specs/003-ai-context-bridge/contracts/bridge.md   # CLI export/impact/mcp + outils MCP
tests/unit/test_repomap.py, test_impact.py, test_tour.py, test_mcp_tools.py
tests/golden/test_repomap_golden.py
tests/integration/test_export_cli.py, test_mcp_server.py (smoke, skip sans extra)
```

**Structure Decision**: nouveau package `bridge/` (production d'artefacts pour
l'extérieur, comme `site/` et `baseline/`) ; impact et tour sont des insights.

## Complexity Tracking

Aucune violation — section vide.
