# Feature Specification: CodeAtlas — Générateur de documentation intelligente

**Feature Branch**: `001-intelligent-doc-generator`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "CodeAtlas — générateur de documentation intelligente par analyse statique. Un développeur ou une équipe pointe l'outil sur un dépôt de code (Python, JavaScript/TypeScript, Java — y compris monorepo polyglotte) et obtient, sans configuration obligatoire, un site de documentation navigable et toujours à jour : diagrammes UML et dépendances avec cycles, graphes d'appels et flux depuis les points d'entrée, détection d'architecture et de patterns, métriques de santé du code, vue unifiée multi-langage pour monorepos. Référence API extraite des docstrings/JSDoc/Javadoc. Sortie MkDocs Material + Mermaid, artefacts intermédiaires exploitables seuls. CLI une-commande + job CI/CD. Déterministe, tolérant aux fichiers non parsables, hors-ligne, sans LLM."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Documenter un dépôt Python en une commande (Priority: P1)

Un développeur lance une seule commande sur un dépôt Python quelconque, sans aucune
configuration préalable, et obtient un site de documentation navigable contenant : la
vue d'ensemble du dépôt, les diagrammes de classes UML par module (héritage,
composition, associations), le diagramme de dépendances entre packages avec les cycles
mis en évidence, et la référence API complète extraite des docstrings.

**Why this priority**: C'est le socle de toute la valeur du produit — sans lui, aucune
autre capacité n'a de support. Il constitue à lui seul un MVP viable (périmètre validé
par le prédécesseur gendoc) et permet de livrer et tester la chaîne complète
analyse → graphe de code → diagrammes → site.

**Independent Test**: Lancer la commande de build sur un package Python d'exemple
versionné dans le repo (contenant héritages, cycles de dépendances, docstrings) et
vérifier que le site produit contient chaque classe, chaque relation attendue et la
référence API, sans erreur.

**Acceptance Scenarios**:

1. **Given** un dépôt Python valide sans fichier de configuration CodeAtlas, **When**
   l'utilisateur exécute la commande de build en pointant la racine du dépôt, **Then**
   un site statique navigable est généré avec vue d'ensemble, diagrammes de classes,
   diagramme de dépendances de packages et référence API par module.
2. **Given** un dépôt contenant un cycle de dépendances entre packages, **When** la
   documentation est générée, **Then** le cycle est visuellement mis en évidence dans
   le diagramme de dépendances et listé dans une section dédiée.
3. **Given** un dépôt contenant un fichier Python syntaxiquement invalide, **When** la
   documentation est générée, **Then** la build réussit, le fichier est listé dans la
   section « éléments non analysés » avec la raison, et le reste du dépôt est documenté.
4. **Given** le même dépôt analysé deux fois de suite, **When** on compare les deux
   sorties, **Then** elles sont strictement identiques.

---

### User Story 2 - Comprendre les flux d'exécution (Priority: P2)

Un développeur qui découvre une base de code veut savoir « que se passe-t-il quand on
appelle ce point d'entrée ? ». La documentation présente, pour chaque point d'entrée
détecté (routes d'API web, commandes CLI, fonctions main), un graphe d'appels et un
diagramme de flux descendant vers les couches basses, avec une profondeur réglable.

**Why this priority**: C'est le premier différenciateur « intelligent » par rapport aux
générateurs de doc classiques — il répond à la question la plus coûteuse de
l'onboarding : comment le code s'exécute réellement.

**Independent Test**: Sur le package d'exemple contenant une CLI et des routes API
factices, vérifier que chaque point d'entrée est détecté et que son graphe d'appels
contient les chaînes d'appel attendues jusqu'à la profondeur demandée.

**Acceptance Scenarios**:

1. **Given** un dépôt exposant des points d'entrée (routes API, CLI, main), **When** la
   documentation est générée, **Then** une section « Points d'entrée » liste chacun
   d'eux avec un diagramme de flux navigable vers les fonctions appelées.
2. **Given** une fonction cible choisie par l'utilisateur, **When** il demande un graphe
   focalisé avec une profondeur N, **Then** le diagramme produit contient les appelants
   et appelés jusqu'à N niveaux, et rien au-delà.
3. **Given** du code utilisant des appels impossibles à résoudre statiquement
   (réflexion, imports dynamiques), **When** le graphe est généré, **Then** les liens
   incertains sont visuellement distingués des liens sûrs et comptabilisés comme tels.

---

### User Story 3 - Évaluer la santé du code (Priority: P2)

Un lead technique consulte dans la documentation un tableau de bord de santé du dépôt :
complexité par module/fonction, taille, couplage entre modules, taux de couverture de la
documentation interne (docstrings), et code probablement mort. Les zones à risque sont
mises en évidence visuellement et navigables jusqu'au symbole concerné.

**Why this priority**: Transforme la documentation en outil de pilotage — valeur forte
pour les équipes et les missions d'audit, mais dépend du graphe de code du P1.

**Independent Test**: Sur le package d'exemple contenant des fonctions volontairement
complexes, non documentées et non référencées, vérifier que les métriques attendues
apparaissent avec les bonnes valeurs et que les éléments à risque sont signalés.
(Sans les graphes d'appels de la story 2, la détection de code mort se replie sur les
seules références entrantes — la story reste testable indépendamment.)

**Acceptance Scenarios**:

1. **Given** un dépôt analysé, **When** la documentation est générée, **Then** une page
   « Santé du code » présente par module : complexité, taille, couplage, couverture de
   docstrings, avec des seuils visuels (sain / à surveiller / critique).
2. **Given** une fonction jamais référencée dans le graphe d'appels, **When** la page
   santé est générée, **Then** elle apparaît dans la liste « code probablement mort »
   avec le niveau de confiance associé.
3. **Given** deux exécutions sur le même code, **When** on compare les métriques,
   **Then** les valeurs sont identiques (aucune mesure dépendante de l'environnement).

---

### User Story 4 - Documentation toujours à jour via la CI (Priority: P2)

Une équipe branche CodeAtlas dans son pipeline d'intégration continue : à chaque push,
la documentation est régénérée et publiée automatiquement. En cas de problème d'analyse,
le pipeline le signale sans bloquer la publication du reste.

**Why this priority**: C'est ce qui élimine la dérive documentaire — la promesse
centrale du produit ; simple à livrer dès que le P1 existe.

**Independent Test**: Configurer le job CI sur un dépôt d'exemple, pousser un commit
modifiant une classe, et vérifier que la documentation publiée reflète le changement
sans intervention manuelle.

**Acceptance Scenarios**:

1. **Given** un dépôt configuré avec le job CI CodeAtlas, **When** un commit est poussé,
   **Then** la documentation est régénérée et publiée, et le résultat (succès,
   avertissements, éléments ignorés) est visible dans le compte rendu du pipeline.
2. **Given** un mode « vérification » activé en CI, **When** l'analyse détecte des
   régressions définies par l'équipe (nouveau cycle de dépendances, chute de couverture
   de docstrings sous un seuil), **Then** le job échoue avec un rapport explicite.

---

### User Story 5 - Visualiser l'architecture et les patterns (Priority: P3)

Un architecte consulte une vue « Architecture » générée automatiquement : les couches
détectées (présentation, domaine, infrastructure…), les composants et leurs frontières,
les design patterns reconnus (factory, singleton, observer…), et les violations
(dépendance d'une couche basse vers une couche haute, cycles inter-composants).

**Why this priority**: Forte valeur différenciante mais dépend de la maturité du graphe
de code (P1) et du graphe d'appels (P2) ; les heuristiques demandent plus d'itérations.

**Independent Test**: Sur un package d'exemple structuré en couches avec des patterns
connus et une violation volontaire, vérifier que les couches, les patterns et la
violation sont détectés et restitués.

**Acceptance Scenarios**:

1. **Given** un dépôt organisé en couches identifiables, **When** la documentation est
   générée, **Then** une vue architecture présente les couches détectées et les
   dépendances entre elles, chaque affirmation étant traçable vers les éléments de code
   qui la justifient.
2. **Given** une dépendance violant le sens des couches détectées, **When** la vue est
   générée, **Then** la violation est signalée avec les éléments impliqués.
3. **Given** une classe implémentant un pattern reconnu, **When** la documentation est
   générée, **Then** le pattern est mentionné sur la page de la classe avec les indices
   ayant conduit à la détection.

---

### User Story 6 - Documenter un monorepo polyglotte (Priority: P3)

Une équipe pointe CodeAtlas sur un monorepo contenant un front TypeScript, un back
Python et des services Java. L'outil détecte chaque sous-projet, applique l'analyseur
adapté à chaque langage, et produit un site unique : navigation croisée entre les
sous-projets, référence API extraite des docstrings/JSDoc/Javadoc, et graphe de
dépendances inter-services.

**Why this priority**: C'est la vision cible complète, mais elle exige que le socle
(P1–P3) soit stable et que le modèle interne soit réellement indépendant du langage.
Livrable par incréments : d'abord JavaScript/TypeScript, puis Java.

**Independent Test**: Sur un monorepo d'exemple (front TS + back Python + service
Java), vérifier que les trois sous-projets sont détectés, documentés dans un site
unique, et que le graphe inter-services reflète les dépendances déclarées.

**Acceptance Scenarios**:

1. **Given** un monorepo avec plusieurs sous-projets de langages différents, **When**
   la documentation est générée, **Then** chaque sous-projet est détecté
   automatiquement et documenté avec les mêmes types de vues que le P1, dans un site
   unique à navigation croisée.
2. **Given** des dépendances entre sous-projets (appels d'API, imports partagés,
   dépendances déclarées), **When** la vue monorepo est générée, **Then** un graphe
   inter-services présente ces liens avec leur nature.
3. **Given** un sous-projet dans un langage non supporté, **When** la documentation est
   générée, **Then** le sous-projet est listé comme non analysé et le reste du monorepo
   est documenté normalement.

---

### Edge Cases

- Dépôt vide ou sans aucun fichier d'un langage supporté : message clair et code de
  sortie explicite, pas de site vide silencieux.
- Fichiers non parsables (syntaxe invalide, encodage inconnu, version de langage non
  supportée) : signalés dans la doc et le rapport, jamais bloquants (sauf si 100 % des
  fichiers sont inanalysables).
- Constructions dynamiques (réflexion, imports dynamiques, monkey-patching,
  métaprogrammation) : analyse best-effort, liens marqués « incertains », limites
  documentées — jamais de fausse certitude.
- Très gros dépôts (≥ 50 000 lignes) : performance maîtrisée, possibilité d'exclure des
  chemins ; dossiers générés/vendorés (dépendances installées, artefacts de build)
  exclus par défaut.
- Noms Unicode, liens symboliques, fichiers dupliqués : gérés sans crash ni doublons
  dans la sortie.
- Symboles sans documentation interne (docstring/JSDoc/Javadoc absente) : la référence
  API affiche la signature et signale l'absence, comptabilisée dans la métrique de
  couverture.
- Deux exécutions concurrentes sur le même dépôt : pas de corruption de la sortie.

## Requirements *(mandatory)*

### Functional Requirements

#### Analyse

- **FR-001**: Le système DOIT analyser un dépôt de code par analyse statique
  uniquement, sans exécuter le code analysé, sans accès réseau et sans service externe.
- **FR-002**: Le système DOIT construire une représentation interne unique du code
  (modules, types, fonctions, attributs, relations d'héritage/composition/association,
  imports, appels) indépendante du langage source.
- **FR-003**: Le système DOIT supporter l'analyse du Python en priorité 1, de
  JavaScript/TypeScript en priorité 2 et de Java en priorité 3, via des analyseurs
  interchangeables produisant la même représentation interne.
- **FR-004**: Le système DOIT continuer l'analyse quand un fichier est inanalysable, le
  consigner (chemin, raison) et le restituer dans la documentation et le rapport.
- **FR-005**: Le système DOIT produire des sorties strictement déterministes : même
  entrée → sorties identiques octet pour octet.
- **FR-006**: Le système DOIT exclure par défaut les répertoires de dépendances
  installées et d'artefacts générés, et permettre d'ajouter des motifs d'exclusion.

#### Restitution

- **FR-007**: Le système DOIT générer des diagrammes de classes par module (héritage,
  composition, agrégation, association, dépendance) dans un format texte versionnable
  rendu graphiquement dans le site.
- **FR-008**: Le système DOIT générer le diagramme des dépendances entre packages avec
  détection et mise en évidence des cycles.
- **FR-009**: Le système DOIT détecter les points d'entrée (routes API web, commandes
  CLI, fonctions principales) et générer pour chacun un graphe d'appels/diagramme de
  flux, avec profondeur réglable et distinction visuelle des liens incertains.
- **FR-010**: Le système DOIT permettre un diagramme focalisé sur un symbole donné
  (classe ou fonction) à profondeur N.
- **FR-011**: Le système DOIT extraire la documentation interne (docstrings, JSDoc,
  Javadoc) et produire une référence API complète organisée par module/package.
- **FR-012**: Le système DOIT calculer et restituer des métriques par module et par
  symbole : complexité, taille, couplage, couverture de documentation interne, et code
  probablement mort avec niveau de confiance (le code mort est restitué sur la page
  santé comme détection traçable, non comme métrique chiffrée).
- **FR-013**: Le système DOIT détecter couches, composants, design patterns et
  violations d'architecture, chaque détection étant traçable vers les éléments de code
  qui la justifient.
- **FR-014**: Le système DOIT produire un site statique navigable consultable
  hors-ligne, et des artefacts intermédiaires (pages, diagrammes, images) exploitables
  indépendamment du site.
- **FR-015**: Pour un monorepo, le système DOIT détecter les sous-projets et leurs
  langages, documenter chacun, et produire une vue unifiée avec navigation croisée et
  graphe de dépendances inter-services.

#### Utilisation

- **FR-016**: L'utilisateur DOIT pouvoir générer la documentation complète avec une
  seule commande pointant la racine du dépôt, sans configuration obligatoire.
- **FR-017**: Le système DOIT accepter une configuration optionnelle (fichier au format
  texte versionnable) pour : exclusions, profondeur des graphes, seuils de métriques,
  éléments privés/publics, titre et langue du site.
- **FR-018**: Le système DOIT être intégrable en pipeline CI : exécution non
  interactive, codes de sortie significatifs, rapport lisible en sortie de job, et mode
  « vérification » faisant échouer le job sur des seuils définis par l'équipe.
- **FR-019**: Le système DOIT exposer ses capacités sous forme de bibliothèque
  utilisable programmatiquement, la ligne de commande n'étant qu'une façade.
- **FR-020**: Le système DOIT restituer un résumé de fin d'exécution : éléments
  analysés, ignorés, avertissements, durée.

### Key Entities

- **Graphe de code** : représentation interne unifiée du dépôt — nœuds (module, type,
  fonction, attribut, sous-projet) et arêtes (héritage, composition, import, appel,
  dépendance inter-services), chaque arête portant un niveau de certitude.
- **Sous-projet** : unité détectée dans un monorepo — langage, racine, manifeste,
  éléments analysés.
- **Diagramme** : vue générée depuis le graphe de code (classes, dépendances, flux,
  architecture) — type, périmètre, profondeur, format de sortie.
- **Métrique** : mesure calculée rattachée à un nœud du graphe — nom, valeur, seuils,
  statut (sain / à surveiller / critique).
- **Détection** : fait architectural inféré (couche, composant, pattern, violation,
  code mort) — type, éléments concernés, indices justificatifs, niveau de confiance.
- **Rapport d'analyse** : synthèse d'une exécution — éléments analysés/ignorés avec
  raisons, avertissements, métriques globales, durée.
- **Site de documentation** : ensemble navigable produit — pages, diagrammes,
  référence API, tableau de bord santé, vues architecture et monorepo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sur un dépôt de 50 000 lignes, la documentation complète est générée en
  moins de 30 secondes sur une machine de développement standard, avec une seule
  commande et zéro configuration.
- **SC-002**: Deux exécutions successives sur le même dépôt produisent des sorties
  identiques octet pour octet, sur les trois langages supportés.
- **SC-003**: 100 % des classes et fonctions publiques d'un dépôt analysable
  apparaissent dans la référence API générée.
- **SC-004**: Sur un dépôt contenant des fichiers inanalysables, la génération aboutit
  et 100 % des fichiers ignorés sont listés avec leur raison.
- **SC-005**: Un développeur découvrant un dépôt inconnu identifie ses composants
  principaux, leurs dépendances et un flux d'exécution de bout en bout en moins de
  10 minutes en n'utilisant que la documentation générée.
- **SC-006**: La documentation publiée reflète tout changement de code en moins de
  5 minutes après un push, sans aucune intervention manuelle.
- **SC-007**: L'exécution complète ne déclenche aucun appel réseau (vérifiable en
  environnement isolé).
- **SC-008**: Sur le corpus d'exemple versionné, 100 % des cycles de dépendances, des
  points d'entrée et des patterns volontairement introduits sont détectés, sans fausse
  détection sur les contre-exemples du corpus.

## Assumptions

- Le site généré est en anglais par défaut ; la langue (dont le français) est
  configurable via la configuration optionnelle (FR-017).
- Les exclusions par défaut couvrent les conventions usuelles des trois écosystèmes
  (dépendances installées, environnements virtuels, artefacts de build, dossiers
  cachés).
- La détection des sous-projets d'un monorepo s'appuie sur les manifestes standards de
  chaque écosystème (déclaration de package Python, manifeste npm, build Java).
- Les graphes d'appels et la détection de code mort sont « best-effort » face au code
  dynamique : les limites sont documentées et les liens incertains explicitement
  marqués (jamais présentés comme sûrs).
- Le tableau de bord santé restitue des métriques calculées statiquement ; la
  couverture de tests d'exécution est hors périmètre v1.
- Les briques éprouvées du projet antérieur gendoc (analyse Python, rendu de
  diagrammes, construction du site) sont réutilisées après adaptation aux principes de
  la constitution ; leur périmètre fonctionnel correspond au P1.
- La génération de texte par IA (résumés, explications rédigées) est explicitement hors
  périmètre : toute l'« intelligence » provient d'analyse statique.
- L'édition manuelle de pages complémentaires (guides rédigés à la main) reste possible
  et n'est jamais écrasée par la régénération.
