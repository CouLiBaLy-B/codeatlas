# Feature Specification: Détection de la racine des sources — un graphe juste sur les vrais dépôts

**Feature Branch**: `005-source-root-detection`

**Created**: 2026-07-19

**Status**: Draft

**Input**: User description: "Le dogfooding (lancer CodeAtlas sur son propre code) a
montré que sur un projet en layout `src/`, aucune dépendance d'import n'est résolue :
les modules sont nommés d'après leur chemin (`src.codeatlas.api`) alors que le code
importe `codeatlas.api`. Résultat : graphe d'architecture vide, couplage nul partout,
faux sous-projets issus des répertoires de sortie générés. Rendre l'analyse juste sur
les dépôts réels."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dépendances justes sur un projet en layout `src/` (Priority: P1)

Un développeur analyse un projet Python organisé selon la convention `src/`
(le package vit dans `src/monpaquet/`, comme le recommande l'écosystème Python
moderne). CodeAtlas identifie que `src/` est la racine d'import : les modules sont
nommés `monpaquet.module` — le nom réellement importable — et les instructions
`from monpaquet.module import X` se résolvent en arêtes de dépendance. Le graphe
d'architecture, les dépendances de packages, le couplage (fan-in/fan-out), les cycles
et les couches reflètent la vraie structure, au lieu d'être vides.

**Why this priority**: c'est la cause directe du symptôme observé (graphe vide,
couplage nul) et elle touche la majorité des projets Python modernes ; sans elle,
toute l'analyse en aval est fausse sur ces dépôts.

**Independent Test**: analyser un projet en layout `src/` (CodeAtlas lui-même depuis
la racine du dépôt) et vérifier que les arêtes d'import passent de zéro à un nombre
correspondant aux dépendances réelles, et que le couplage par module n'est plus nul.

**Acceptance Scenarios**:

1. **Given** un dépôt dont le package est sous `src/`, **When** l'analyse est lancée
   depuis la racine du dépôt, **Then** les modules portent leur nom importable
   (sans le segment `src`) et les imports internes se résolvent en arêtes.
2. **Given** ce même dépôt, **When** on consulte les dépendances de packages et le
   couplage, **Then** ils reflètent les imports réels (non vides, non nuls).
3. **Given** un dépôt SANS layout `src/` (package à la racine), **When** il est
   analysé, **Then** le résultat est strictement inchangé par rapport à aujourd'hui
   (aucune régression).
4. **Given** deux analyses successives du même dépôt, **Then** les sorties sont
   identiques octet pour octet (la détection est déterministe).

---

### User Story 2 - Racine d'import correcte quel que soit l'emplacement du package (Priority: P2)

Le package d'un projet n'est pas toujours à la racine ni sous `src/` : il peut vivre
dans un sous-répertoire (`lib/`, `python/`, le nom du produit…). CodeAtlas déduit la
racine d'import à partir de la structure réelle des packages (présence de fichiers
d'initialisation, chaîne de packages remontant jusqu'à un répertoire non-package),
plutôt que de supposer que la racine analysée est la racine d'import. Les noms de
modules et donc les dépendances sont corrects sans configuration.

**Why this priority**: généralise la story 1 à tous les agencements réels ; utile mais
le cas `src/` couvre déjà la majorité des projets.

**Independent Test**: analyser un dépôt où le package est dans un sous-répertoire
quelconque et vérifier que les noms de modules correspondent aux imports du code, sans
réglage manuel.

**Acceptance Scenarios**:

1. **Given** un package situé dans un sous-répertoire arbitraire, **When** l'analyse
   tourne, **Then** les modules sont nommés relativement à la racine d'import déduite,
   pas à la racine analysée.
2. **Given** plusieurs packages indépendants dans des sous-répertoires distincts,
   **When** l'analyse tourne, **Then** chacun est nommé depuis sa propre racine
   d'import.
3. **Given** un cas ambigu où la racine ne peut être déduite avec certitude, **Then**
   le comportement actuel (nom d'après le chemin analysé) est conservé comme repli
   sûr, et le choix reste déterministe.

---

### User Story 3 - Les répertoires générés ne polluent pas l'analyse (Priority: P3)

Un développeur analyse un dépôt qui contient des artefacts générés (sites de
documentation déjà produits, dossiers de build, dépendances installées). Ces
répertoires ne doivent pas être analysés : ils créent de faux modules et de faux
sous-projets (par exemple un sous-projet « JavaScript » fait des scripts vendorisés
d'un site déjà généré) qui brouillent le graphe et les métriques.

**Why this priority**: améliore la justesse sur les dépôts réels et supprime le bruit
observé au dogfooding ; moins central que la résolution des noms de modules.

**Independent Test**: analyser un dépôt contenant un répertoire de sortie CodeAtlas et
un dossier de build, et vérifier qu'aucun module n'en provient et qu'aucun sous-projet
parasite n'apparaît.

**Acceptance Scenarios**:

1. **Given** un dépôt contenant un répertoire de sortie de documentation généré,
   **When** l'analyse tourne sans configuration particulière, **Then** aucun fichier
   de ce répertoire n'est analysé.
2. **Given** des dossiers de build ou d'artefacts courants, **Then** ils sont ignorés
   par défaut, au même titre que les dépendances installées le sont déjà.
3. **Given** un utilisateur qui souhaite malgré tout analyser un tel répertoire,
   **Then** il peut le réintégrer explicitement par configuration (les exclusions par
   défaut restent surchargeable).

---

### Edge Cases

- Package sous `src/` mais importé via le chemin complet incluant `src` (rare, projet
  mal configuré) : la détection ne doit pas dégrader ce cas au point de tout casser —
  le repli sûr s'applique.
- Modules « orphelins » (scripts à la racine, sans package) : conservent un nom
  raisonnable et n'empêchent pas la détection pour le reste.
- Répertoire `src/` contenant plusieurs packages de premier niveau : chacun est un
  package importable distinct sous la même racine d'import.
- Fichier `src/` qui n'est pas un répertoire de package (juste un dossier nommé `src`
  contenant du code non packagé) : la détection ne doit pas inventer une racine
  erronée.
- Monorepo où chaque sous-projet a son propre layout `src/` : la racine d'import est
  déduite par sous-projet, indépendamment.
- Autres langages (JavaScript/TypeScript, Java) : leur résolution de noms suit leurs
  propres conventions et ne doit pas être altérée par cette feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: L'analyse Python DOIT déduire la racine d'import d'un package et nommer
  les modules d'après cette racine (nom réellement importable), et non d'après la
  racine du répertoire analysé lorsqu'elles diffèrent.
- **FR-002**: La convention `src/` (package sous un répertoire `src` qui n'est pas
  lui-même un package) DOIT être reconnue : le segment `src` ne DOIT pas apparaître
  dans les noms de modules.
- **FR-003**: Les instructions d'import internes DOIVENT se résoudre en arêtes de
  dépendance dès lors que le nom de module cible correspond à un module analysé, y
  compris pour les projets en layout `src/`.
- **FR-004**: La détection DOIT être purement statique et déterministe : deux analyses
  du même dépôt produisent des noms de modules et des arêtes identiques.
- **FR-005**: Un dépôt dont le package est déjà à la racine analysée DOIT produire un
  résultat inchangé (aucune régression sur les projets non-`src`).
- **FR-006**: En cas d'ambiguïté sur la racine d'import, l'analyse DOIT retomber sur
  le comportement actuel (nom d'après le chemin analysé) plutôt que de deviner, et ce
  repli DOIT rester déterministe.
- **FR-007**: La racine d'import DOIT être déduite par sous-projet en contexte
  monorepo, sans supposer une racine commune.
- **FR-008**: Les répertoires de sortie et d'artefacts générés courants (sites de
  documentation produits, dossiers de build) DOIVENT être exclus de l'analyse par
  défaut, l'utilisateur pouvant les réintégrer par configuration.
- **FR-009**: Cette feature ne DOIT modifier ni le contrat de l'IR ni la résolution de
  noms des autres langages ; seuls les noms de modules Python (et les arêtes qui en
  découlent) changent pour les dépôts concernés.

### Key Entities

- **Racine d'import** : répertoire à partir duquel les noms de modules qualifiés sont
  calculés pour un ensemble de sources — peut différer de la racine analysée
  (cas `src/` ou package en sous-répertoire).
- **Nom de module qualifié** : identité importable d'un module (`paquet.sous.module`)
  telle qu'un `import` la désigne — c'est la clé qui doit correspondre entre le nom
  d'un module et la cible d'un import.
- **Exclusions par défaut** : ensemble de motifs de répertoires jamais analysés sauf
  réintégration explicite (dépendances installées, build, sorties générées).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sur un projet Python en layout `src/` (CodeAtlas lui-même), la
  proportion d'imports internes résolus en arêtes passe de 0 % à un niveau comparable
  à celui obtenu en analysant directement le répertoire des sources (référence
  observée : de 0 à ~176 arêtes d'import sur ce dépôt).
- **SC-002**: Le couplage (fan-in/fan-out) et les dépendances de packages sont non
  nuls et cohérents avec les imports réels sur un projet en layout `src/`.
- **SC-003**: Aucune régression : sur les corpus d'exemple existants sans layout
  `src/`, toutes les sorties restent identiques octet pour octet.
- **SC-004**: Deux analyses successives du même dépôt produisent des sorties
  identiques octet pour octet (déterminisme préservé).
- **SC-005**: Sur un dépôt contenant un répertoire de documentation généré, zéro
  module et zéro sous-projet ne proviennent de ce répertoire.
- **SC-006**: Aucune dégradation de performance perceptible : le budget
  constitutionnel (50 000 lignes en moins de 30 secondes) reste tenu.

## Assumptions

- La correction porte sur l'analyseur Python (langage où le layout `src/` est une
  convention établie) ; les autres analyseurs conservent leur résolution propre.
- La détection s'appuie sur la structure des packages présente dans les sources (rien
  n'est exécuté, aucun `sys.path` réel n'est consulté) — cohérent avec l'analyse
  statique pure de la constitution.
- Les exclusions par défaut nouvelles visent des conventions largement répandues
  (dossiers de build, sorties de documentation) et restent entièrement surchargeable
  par la configuration existante.
- Les corpus d'exemple versionnés restent la référence de non-régression ; un nouveau
  corpus en layout `src/` sera ajouté pour valider la détection.
