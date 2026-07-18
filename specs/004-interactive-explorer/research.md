# Research: Explorateur interactif

**Feature**: 004-interactive-explorer | **Date**: 2026-07-18

Toutes les inconnues du Technical Context sont résolues ci-dessous. Fil conducteur :
**toute l'intelligence est précalculée en Python au build (déterministe), le
navigateur ne fait que rendre et filtrer** — c'est ce qui réconcilie interactivité et
constitution (principes I et III).

## R1. Rendu du graphe explorable

- **Decision**: Cytoscape.js **vendorisé** (fichier unique minifié, version épinglée
  et empreinte SHA-256 enregistrée dans le repo, comme Mermaid déjà vendorisé dans
  `site/assets`), avec **positions précalculées côté Python** livrées dans les
  données — aucun layout force-directed côté client.
- **Rationale**: pan/zoom/sélection/nœuds composés (agrégation sous-projet → couche →
  module) fournis nativement ; zéro dépendance transitive ; en fixant les positions au
  build, (a) le rendu est déterministe, (b) le client reste fluide même sur de gros
  graphes (pas de simulation physique), (c) le fallback statique Mermaid partage la
  même source de vérité (IR).
- **Alternatives considered**: D3.js (bas niveau, beaucoup de code à écrire et layout
  client non déterministe) ; sigma.js/WebGL (surdimensionné, intégration MkDocs plus
  lourde) ; SVG artisanal (pan/zoom faisable, mais dépliage/compound nodes coûteux à
  réécrire) ; layout côté client (non déterministe — violerait le principe I appliqué
  aux artefacts si le layout était sérialisé, et gèle le navigateur sur gros graphes).

## R2. Calcul de layout déterministe

- **Decision**: layout hiérarchique par niveaux calculé en Python : positionnement
  par couches (algorithme de Sugiyama simplifié : rang topologique → réduction des
  croisements par tri barycentrique à nombre d'itérations fixe → coordonnées
  entières), listes toujours triées, aucune source d'aléa. `networkx` (déjà
  dépendance) fournit rangs et tri topologique.
- **Rationale**: byte-for-byte reproductible ; adapté aux graphes de dépendances
  (orientés, quasi-DAG après agrégation) ; complexité quasi linéaire, compatible avec
  le budget 50 k lignes < 30 s.
- **Alternatives considered**: spring layout networkx avec graine fixe (stable mais
  rendu médiocre pour des couches architecturales, coût O(n²)) ; Graphviz (binaire
  externe chez l'utilisateur — contrainte « aucun runtime externe » de la
  constitution).

## R3. Transport des données vers le navigateur (contrainte `file://`)

- **Decision**: les données de chaque vue sont émises comme **fichiers JS**
  (`atlas-data-*.js` définissant `window.__ATLAS__`), pas comme JSON chargé par
  `fetch()`. JSON canonique à l'intérieur (clés et listes triées, séparateurs fixes,
  UTF-8, fin de ligne unique).
- **Rationale**: `fetch()` sur `file://` est bloqué par les navigateurs ; un `<script
  src>` local fonctionne partout — le site reste consultable sans aucun serveur
  (edge case explicite de la spec). Le JSON canonique garantit le déterminisme.
- **Alternatives considered**: `fetch()` de JSON (casse en `file://`) ; données
  inlinées dans chaque page HTML (dupliquées entre pages, alourdit le site et le
  diff).

## R4. Recherche de symboles hors-ligne

- **Decision**: index de symboles précalculé (entrées triées : nom, type, signature,
  module, langage, cible) + **JS artisanal** (~150 lignes) : correspondance
  préfixe/sous-chaîne, classement déterministe (préfixe exact > préfixe > sous-chaîne,
  puis ordre lexicographique), navigation clavier. Publié comme les autres données
  (R3).
- **Rationale**: chercher des identifiants n'est pas chercher de la prose — pas besoin
  de tokenisation ni de scoring flou ; le classement reste explicable et déterministe
  (FR-007/FR-008) ; zéro dépendance. La recherche plein-texte des pages reste celle de
  MkDocs Material (inchangée, complémentaire).
- **Alternatives considered**: lunr.js (tokenisation orientée prose, scoring opaque) ;
  fuse.js (fuzzy → résultats « approximatifs trompeurs » exclus par la spec) ;
  étendre l'index MkDocs (couplage fort au thème, pas de champs structurés).

## R5. Mode atelier : serveur local + rechargement

- **Decision**: serveur HTTP de la bibliothèque standard (`ThreadingHTTPServer`,
  bind `127.0.0.1` uniquement) servant le site généré ; surveillance fichiers via
  **`watchdog`** (déjà présent dans l'environnement comme dépendance de MkDocs, à
  promouvoir en dépendance directe) ; rechargement navigateur par **polling** d'un
  jeton de build (`/__atlas_build__`) injecté uniquement en mode serve — jamais dans
  les artefacts committables.
- **Rationale**: zéro nouvelle dépendance lourde, aucun websocket, localhost only
  (FR-012) ; le jeton de build hors artefacts préserve le déterminisme des sorties ;
  `mkdocs serve` est écarté car il reconstruit tout le site (incompatible SC-006).
- **Alternatives considered**: `mkdocs serve` (rebuild complet, pas d'analyse
  incrémentale) ; livereload/websockets via starlette+uvicorn (dépendances du seul
  extra `[mcp]`, à ne pas imposer au cœur) ; `watchfiles` (nouvelle dépendance binaire
  alors que watchdog est déjà là).

## R6. Régénération incrémentale

- **Decision**: invalidation à la granularité de l'**unité de sous-projet** : les
  fragments d'IR sont indépendants entre sous-projets (aucune arête de nœuds ne les
  traverse ; les liens inter-services sont recalculés à l'assemblage), donc seules
  les unités possédant les fichiers modifiés sont réanalysées, les fragments des
  autres sont réutilisés tels quels, puis le graphe est réassemblé. Un manifeste
  modifié (pyproject, package.json, codeatlas.toml…) est « structurel » → analyse
  complète et rechargement de la config. Regroupement des événements (debounce
  fixe), la dernière version du disque fait foi. Un fichier devenu invalide bascule
  en avertissement (principe IV) sans arrêter la session. Invariant testé : N cycles
  incrémentaux ≡ analyse complète à froid, octet pour octet.
- **Rationale**: la résolution croisée (appels, imports) opère à l'intérieur d'une
  unité — une granularité plus fine casserait ces arêtes ; l'équivalence stricte
  avec l'analyse à froid reste démontrable, et SC-006 (< 5 s) est tenu.
- **Alternatives considered**: rebuild complet à chaque événement (simple mais
  10-30 s sur 50 k lignes) ; invalidation au niveau fichier ou symbole (casserait la
  résolution croisée intra-sous-projet et l'équivalence avec le build à froid).

## R7. Tableau de bord : tri et vue proportionnelle

- **Decision**: tables triables par JS artisanal mutualisé (tri stable côté client
  sur valeurs pré-embarquées) ; **treemap calculée au build en Python** (algorithme
  squarify, arithmétique entière, ordre déterministe) émise en **SVG cliquable** avec
  liens vers les fiches ; sans JS, la table simple actuelle reste le repli.
- **Rationale**: le SVG précalculé est déterministe, indexable, fonctionne sans JS
  pour l'affichage (les liens SVG sont natifs) ; aucun framework de dataviz à
  vendoriser.
- **Alternatives considered**: bibliothèque de charts (Chart.js, ECharts — lourdes,
  rendu canvas non dégradable) ; treemap côté client (layout non déterministe entre
  navigateurs).

## R8. Extraits de source sur les fiches

- **Decision**: extraits découpés au build à partir des emplacements de l'IR
  (fichier + lignes de définition), repliés par défaut (admonition `???`),
  rendus SANS lexing Pygments (`use_pygments: false` — le lexing de dizaines de
  milliers de lignes embarquées ferait exploser le budget SC-005 ; mesuré :
  26,7 s → 7,5 s sur le corpus 50 k). Option
  `[explorer] include_source = true|false` (défaut `true`) pour les cas sensibles.
- **Rationale**: 100 % statique et déterministe ; aucun JS requis (SC-007) ; l'option
  d'exclusion honore l'assumption de la spec.
- **Alternatives considered**: viewer de code client (charge les sources brutes —
  casse en `file://`, duplique) ; lien vers forge externe (dépend du réseau et de
  l'hébergeur — contraire au hors-ligne).

## R9. Intégration MkDocs Material et repli sans scripts

- **Decision**: enrichissement progressif — chaque page interactive contient d'abord
  le contenu statique actuel (Mermaid, tables) ; les vues interactives se montent
  par-dessus au chargement du JS et se masquent sinon. Les assets (cytoscape vendorisé,
  JS maison, données) passent par `extra_javascript`/`docs/assets/` comme Mermaid
  aujourd'hui.
- **Rationale**: FR-005/SC-007 garantis par construction (le statique est le contenu
  de base, pas un secours généré à part) ; aucun fork du thème.
- **Alternatives considered**: thème/plugin MkDocs custom (maintenance lourde) ; SPA
  dédiée à côté du site (deux artefacts à réconcilier, navigation cassée).

## R10. Où vivent les nouvelles capacités (architecture)

- **Decision**: nouveau package `explorer/` (construction des données de vues :
  graphe explorable, index de recherche, treemap, layout) consommant uniquement
  `CodeGraph` + insights ; nouveau package `serve/` (session d'atelier : watch,
  invalidation, serveur HTTP). `site/` reste l'assemblage MkDocs et gagne les
  templates/partials interactifs. API publique dans `api.py`, CLI façade dans
  `cli.py` (principe II).
- **Rationale**: symétrie avec l'existant (`bridge/`, `baseline/` : production
  d'artefacts pour l'extérieur) ; `explorer/` testable sans navigateur ni serveur ;
  `serve/` testable sans watch réel (injection d'événements).
- **Alternatives considered**: tout dans `site/` (mélange assemblage et calcul,
  grossit un module déjà central) ; extra optionnel `[serve]` (rejeté : aucune
  dépendance nouvelle lourde, le mode atelier fait partie de la promesse produit).

## Risques identifiés (à surveiller en implémentation)

- Taille des données embarquées sur très gros dépôts → budget par niveau d'agrégation
  (le niveau symbole n'est jamais dans le graphe global, uniquement dans les fiches).
- Déterminisme du JS vendorisé → version épinglée + SHA-256 vérifié par un test.
- Watchdog sur systèmes de fichiers exotiques (NFS…) → repli polling de watchdog,
  documenté dans quickstart.
