# Research: Détection de la racine des sources

**Feature**: 005-source-root-detection | **Date**: 2026-07-19

Fil conducteur : le nom d'un module DOIT être celui qu'un `import` désigne. Aujourd'hui
`module_qualname` (analyzers/python/analyzer.py) dérive le nom du chemin relatif à la
racine analysée — faux dès que la racine d'import est en dessous (layout `src/`,
package en sous-répertoire). Tout se joue statiquement, sans exécuter ni consulter un
`sys.path` réel (constitution I).

## R1. Algorithme de détection de la racine d'import

- **Decision**: pour chaque fichier `.py`, remonter la chaîne des répertoires
  **tant que le parent contient `__init__.py`** ; le nom qualifié est la suite des
  répertoires-packages depuis le premier ancêtre SANS `__init__.py` (la racine
  d'import) jusqu'au fichier. C'est l'algorithme d'import standard, appliqué à la
  structure de fichiers présente dans les sources.
- **Rationale**: purement statique et déterministe ; couvre `src/` (le dossier `src`
  n'a pas d'`__init__.py`, il devient racine d'import et disparaît du nom), le package
  à la racine (racine d'import = racine analysée → comportement actuel), et le package
  en sous-répertoire ; aucune dépendance à l'environnement.
- **Alternatives considered**: lire les `[tool.setuptools] package-dir` / `src` dans
  `pyproject.toml` (fragile, incomplet, pas toujours présent) ; consulter `sys.path`
  (violerait « aucune exécution ») ; heuristique « dossier nommé src » en dur (rate
  les packages en sous-répertoire, et un dossier `src` non-package deviendrait racine
  à tort).

## R2. Modules « orphelins » (hors package)

- **Decision**: un fichier `.py` dont le répertoire n'a pas d'`__init__.py` est un
  module de premier niveau ; son nom est son seul `stem`, sa racine d'import est son
  répertoire. Les scripts à la racine gardent donc un nom raisonnable et ne créent pas
  de racine d'import erronée.
- **Rationale**: reflète la réalité d'import (`python mod.py` ou `import mod` depuis ce
  dossier) ; évite d'inventer un package.
- **Alternatives considered**: rattacher les orphelins au package le plus proche
  (incorrect, produirait de fausses arêtes).

## R3. Où appliquer la re-dérivation

- **Decision**: calculer, à la découverte des fichiers d'un sous-projet, la racine
  d'import de chaque fichier (R1) et fournir à l'analyseur le **nom qualifié** plutôt
  que de le laisser dériver du chemin. `module_qualname` devient une fonction de
  (chemin, racine d'import) ; l'emplacement source (`Location.file`) reste le chemin
  relatif au dépôt (inchangé — les extraits de source et la navigation continuent de
  fonctionner).
- **Rationale**: sépare deux notions aujourd'hui confondues — l'**identité importable**
  (pour les arêtes) et l'**emplacement disque** (pour l'affichage). Seule la première
  change ; l'IR et l'aval ne voient qu'un nom de module corrigé.
- **Alternatives considered**: re-préfixer après coup dans l'API (comme
  `_reroot_fragment` pour les monorepos) — mais le nom qualifié est utilisé DANS
  l'analyseur pour résoudre les imports et enregistrer les symboles ; il faut le bon
  nom dès la construction, pas après.

## R4. Détection par sous-projet (monorepo)

- **Decision**: la racine d'import est déduite par fichier, donc automatiquement par
  sous-projet — chaque sous-projet peut avoir son propre `src/`. Aucune hypothèse de
  racine commune.
- **Rationale**: FR-007 ; l'algorithme R1 est local à chaque arborescence de package.
- **Alternatives considered**: une racine d'import globale par dépôt (casserait les
  monorepos hétérogènes).

## R5. Repli sûr en cas d'ambiguïté

- **Decision**: si la remontée ne tranche pas (ex. arborescence incohérente), retomber
  sur le comportement actuel (nom = chemin relatif à la racine analysée). Le repli est
  déterministe et n'aggrave jamais un cas qui marchait.
- **Rationale**: FR-006 ; tolérance (constitution IV) — jamais de dégradation nette.

## R6. Non-régression sur les projets sans `src/`

- **Decision**: pour un package déjà à la racine analysée, la racine d'import déduite
  EST la racine analysée → noms de modules inchangés → sorties identiques. Les corpus
  d'exemple (python-demo : package `shopdemo` à la racine) ne bougent pas.
- **Rationale**: SC-003 ; garanti par construction, verrouillé par les goldens
  existants (aucune régénération attendue).
- **Alternatives considered**: activer la détection derrière une option (rejeté :
  la justesse doit être le défaut, pas un opt-in).

## R7. Exclusion des répertoires générés (FR-008)

- **Decision**: deux niveaux complémentaires. (a) CodeAtlas dépose un **fichier
  marqueur** discret (ex. `.codeatlas-generated`) à la racine de tout site qu'il
  génère ; l'analyse ignore tout répertoire contenant ce marqueur — robuste et
  spécifique, aucun faux positif. (b) Ajouter aux exclusions par défaut les dossiers
  d'artefacts très répandus non encore couverts (ex. `**/site/` de MkDocs) uniquement
  s'ils sont sans ambiguïté ; sinon s'en remettre au marqueur.
- **Rationale**: le marqueur règle proprement le cas du dogfooding (sorties CodeAtlas
  imbriquées) sans deviner ; les exclusions par défaut restent surchargeable
  (FR-008).
- **Alternatives considered**: exclure `docs/` par défaut (beaucoup de projets ont un
  `docs/` légitime — faux positifs) ; lire `.gitignore` (hors périmètre, sémantique
  différente, non déterministe selon l'état git).

## R8. Corpus de validation

- **Decision**: ajouter un petit corpus versionné en layout `src/`
  (`examples/src-layout-demo/` : `src/mypkg/...` avec imports internes) pour valider
  la détection et le golden associé ; réutiliser CodeAtlas lui-même comme validation
  grandeur nature (SC-001).
- **Rationale**: constitution V — chaque comportement validé contre un exemple réaliste
  versionné.

## Risques

- Un projet qui importe réellement via `src.` (mal configuré) verrait ses noms changer.
  Mitigé par le repli (R5) et par le fait que ce cas est rare et déjà cassé à l'import.
- Le marqueur de génération (R7) doit rester HORS des artefacts committables du site
  utilisateur s'il pouvait fausser un diff — à trancher au plan : soit non écrit dans
  le site final, soit documenté comme attendu.
