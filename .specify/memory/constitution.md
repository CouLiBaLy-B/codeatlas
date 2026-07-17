<!--
Sync Impact Report
- Version : (template) → 1.0.0
- Principes modifiés : création initiale (I à V)
- Sections ajoutées : Contraintes techniques ; Workflow de développement
- Sections supprimées : aucune
- Templates :
  - .specify/templates/plan-template.md ✅ compatible (le "Constitution Check" référence ce fichier)
  - .specify/templates/spec-template.md ✅ compatible (aucune section obligatoire ajoutée)
  - .specify/templates/tasks-template.md ✅ compatible (discipline test-first déjà reflétée)
- TODO différés : aucun
-->

# Constitution de CodeAtlas

CodeAtlas est un générateur de documentation intelligente : il analyse statiquement des
bases de code multi-langages (Python, JavaScript/TypeScript, Java) et produit un site de
documentation navigable (MkDocs Material) contenant diagrammes UML, graphes d'appels et
de flux, détection d'architecture et de patterns, métriques de santé du code et une vue
unifiée pour les monorepos polyglottes.

## Principes fondamentaux

### I. Analyse statique déterministe (NON NÉGOCIABLE)

Toute la « intelligence » de CodeAtlas provient d'analyse statique. À l'exécution,
l'outil ne DOIT faire appel à aucun LLM, aucun service réseau et aucune source de
non-déterminisme : deux exécutions sur le même code source DOIVENT produire des sorties
strictement identiques (octet pour octet, listes triées, aucun horodatage dans les
artefacts). Rationale : la documentation générée doit être diffable, versionnable et
reproductible en CI sans coût ni dépendance externe.

### II. Bibliothèque d'abord, CLI en façade

Chaque capacité DOIT exister d'abord comme API de bibliothèque Python documentée et
testable indépendamment ; la CLI (et l'intégration CI) n'est qu'une façade fine
au-dessus de cette API. Les sorties de la CLI DOIVENT être exploitables en script
(codes retour significatifs, option de sortie JSON pour les résultats d'analyse).
Rationale : hérité de gendoc — l'usage programmatique et l'intégration CI/CD sont des
cas d'usage de premier rang, pas des ajouts tardifs.

### III. Représentation intermédiaire unifiée multi-langage

Les analyseurs de langage DOIVENT produire une représentation intermédiaire (IR)
commune — un graphe de code unique (modules, types, fonctions, appels, dépendances) —
et TOUT ce qui est en aval (diagrammes, métriques, détection de patterns, site) ne DOIT
consommer que cette IR, jamais les AST spécifiques d'un langage. Ajouter un langage =
écrire un nouvel adaptateur respectant le contrat de l'IR, sans modifier le cœur.
Rationale : c'est la condition de la vue multi-langage unifiée et de l'extensibilité.

### IV. Tolérance aux défaillances d'analyse

Un fichier non parsable, une syntaxe inconnue ou une construction non supportée ne DOIT
jamais faire échouer la génération : l'élément est signalé (avertissement structuré,
section « fichiers ignorés » dans la doc) et l'analyse continue. Un échec bloquant n'est
acceptable que si aucun fichier n'a pu être analysé. Rationale : sur du code réel, la
doc partielle et honnête vaut mieux qu'une build cassée (acquis du « tolerant mode » de
gendoc).

### V. Test-first et qualité mesurée

Le développement suit la discipline test-first : les tests d'un comportement DOIVENT
être écrits et validés en échec avant son implémentation. La couverture globale DOIT
rester ≥ 80 % (seuil imposé en CI). Chaque analyseur de langage DOIT être validé contre
un package d'exemple réaliste versionné dans le repo (héritages, cycles, patterns), et
les rendus (Mermaid, site) contre des sorties de référence (« golden files »).
Rationale : un outil qui documente la santé du code des autres doit être exemplaire sur
la sienne.

## Contraintes techniques

- Python ≥ 3.11 pour le cœur ; parsing multi-langage via des parseurs embarqués (aucun
  compilateur ou runtime externe requis chez l'utilisateur).
- Sortie principale : site MkDocs Material avec rendu Mermaid natif ; les artefacts
  intermédiaires (.md, .mmd, .svg) restent exploitables seuls.
- Distribution : package PyPI (CLI `codeatlas`) et GitHub Action officielle.
- Performance : analyse d'un repo de ~50 000 lignes en moins de 30 secondes sur une
  machine de développement standard ; pas de dégradation super-linéaire.
- Aucune dépendance cloud ; licence MIT ; fonctionne hors-ligne.

## Workflow de développement

- Toute fonctionnalité suit le cycle spec-kit : `specify` → (`clarify`) → `plan` →
  `tasks` → `implement`, avec une branche et un dossier `specs/<feature>/` dédiés.
- Le « Constitution Check » du plan DOIT être validé avant toute implémentation ; tout
  écart est justifié par écrit dans le plan (section Complexity Tracking) ou refusé.
- CI obligatoire sur chaque PR : lint, typage, tests, couverture ≥ 80 %, régénération
  de la doc d'exemple sans erreur.
- Les briques éprouvées de gendoc (analyseur AST Python, renderers Mermaid/PlantUML,
  builder MkDocs) sont réutilisées par adaptation explicite : le code importé est
  retravaillé pour respecter les principes I à IV, jamais copié tel quel sans tests.

## Gouvernance

Cette constitution prime sur toute autre pratique du projet. Tout amendement est
documenté dans ce fichier avec passage de version sémantique (MAJOR : retrait ou
redéfinition incompatible d'un principe ; MINOR : ajout de principe ou extension
matérielle ; PATCH : clarification), et son impact est propagé aux templates
`.specify/templates/*`. Chaque revue de PR DOIT vérifier la conformité aux principes ;
la complexité non justifiée est refusée.

**Version**: 1.0.0 | **Ratified**: 2026-07-17 | **Last Amended**: 2026-07-17
