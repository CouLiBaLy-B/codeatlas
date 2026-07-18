# Research: Pont IA

**Date**: 2026-07-18 | **Feature**: [spec.md](spec.md)

## R1. Format et priorisation de la carte (RepoMap)

**Décision**: markdown compact déterministe, budget en **caractères** (config
`[export] budget = 24000`, `--budget` prioritaire). Sections dans l'ordre :
(1) en-tête — dépôt, sous-projets, couches, métriques clés ; (2) points d'entrée ;
(3) parcours de lecture ; (4) API publiques **module par module** — modules
priorisés : ceux portant des points d'entrée d'abord, puis fan-in décroissant, puis
ordre alphabétique ; un module est inclus en entier ou pas du tout. Toute omission
est listée en fin de carte (« Omis (budget) : … ») — jamais silencieuse (FR-002).
Formats : `repomap` (markdown) et `graph` (le JSON canonique de l'IR existant).

**Rationale**: budget en caractères = indépendant de tout fournisseur d'IA (assumé
par la spec) ; le module entier comme unité d'inclusion garde la carte cohérente.

**Alternatives considérées**: budget en tokens (dépend d'un tokenizer tiers —
rejeté) ; coupe au symbole près (cartes incohérentes — rejeté).

## R2. Serveur MCP

**Décision**: SDK Python officiel `mcp` (FastMCP), transport stdio, extra dédié
`codeatlas-doc[mcp]`. Commande `codeatlas mcp PATH` : analyse au démarrage, outils
purs lisant le graphe : `overview`, `search_symbol`, `module_api`, `callers`,
`callees`, `impact`, `dead_code`, `reload`. Résultats bornés (25 correspondances max,
signalé), certitude des liens toujours distinguée, aucune réponse hors graphe.
La logique vit dans des fonctions pures (`bridge/tools.py`) testées sans serveur ;
`server.py` n'est qu'un habillage FastMCP (constitution II).

**Rationale**: MCP = standard de fait 2026 (Claude Code, Cursor, Copilot) ; stdio =
local pur, zéro socket réseau sortante (FR-005, vérifiable).

**Alternatives considérées**: serveur HTTP local — rejeté (surface réseau inutile) ;
implémentation du protocole à la main — rejetée (SDK officiel mature).

## R3. Analyse d'impact

**Décision**: BFS inverse par niveaux sur les arêtes `calls` + `imports` depuis le
symbole (ou tous les symboles d'un fichier), profondeur paramétrable (défaut :
`[graphs].call_depth`). Sortie : niveaux successifs triés, certitude conservée,
points d'entrée atteints marqués (croisement avec `detect_entrypoints`). Implémenté
comme insight (`insights/impact.py`) — consomme l'IR seulement. CLI
`codeatlas impact PATH --focus X [--depth N] [--format text|json]`, aussi exposé
comme outil MCP.

**Rationale**: complément direct du diff (002) ; réutilise la résolution de focus
existante (`_resolve_focus`) et le graphe d'appels.

## R4. Parcours de lecture

**Décision**: ordre déterministe purement structurel : modules des points d'entrée
d'abord (raison « point d'entrée »), puis les autres modules groupés par couche
détectée (présentation → domaine → infrastructure), non assignés en dernier,
alphabétique dans chaque groupe. Chaque étape référence la page de doc du module.
Rendu : section de la carte + page « Parcours de lecture » du site.

**Rationale**: entièrement dérivé de données existantes (entrypoints + architecture),
aucune narration inventée (la sémantique reste à l'assistant de l'utilisateur).

## R5. Emplacements et intégration

**Décision**: `codeatlas export` écrit sur stdout par défaut (`--out FILE` sinon) ;
l'emplacement committable conseillé est `.codeatlas/repomap.md` (déjà exclu de
l'analyse). Aucune nouvelle dépendance du cœur : `mcp` uniquement dans l'extra.
