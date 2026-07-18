# Feature Specification: Pont IA — le substrat déterministe pour les outils d'IA

**Feature Branch**: `003-ai-context-bridge`

**Created**: 2026-07-18

**Status**: Draft

**Input**: User description: "Inspiré d'Understand-Anything (graphe de connaissance
committable consommé par les assistants IA, analyse d'impact, parcours guidés) mais
fidèle à la constitution : CodeAtlas n'appelle JAMAIS de LLM — il produit le contexte
structuré, compact et déterministe que les outils d'IA de l'utilisateur (Claude Code,
Cursor, Copilot…) consomment localement. Le code ne part nulle part : « le substrat
que les outils IA rêvent d'avoir »."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exporter une carte du dépôt prête pour un assistant IA (Priority: P1)

Un développeur exporte une « carte du dépôt » : un document compact et déterministe
(modules, APIs publiques avec signatures, couches, points d'entrée, dépendances
majeures) dimensionné pour tenir dans un budget de contexte configurable. Il la
committe (répertoire dédié versionnable) ou la colle dans son assistant : l'IA raisonne
sur la structure réelle au lieu de deviner.

**Why this priority**: c'est le cœur du positionnement et la brique que tout le reste
consomme ; valeur immédiate sans aucune intégration.

**Independent Test**: exporter la carte du corpus python-demo avec un budget donné,
vérifier qu'elle contient les APIs publiques attendues, respecte le budget, et que
deux exports successifs sont identiques octet pour octet.

**Acceptance Scenarios**:

1. **Given** un dépôt analysable, **When** l'export est demandé, **Then** une carte
   textuelle est produite : vue d'ensemble, sous-projets, couches détectées, points
   d'entrée, APIs publiques par module avec signatures et résumés de doc existants.
2. **Given** un budget de taille configuré, **When** le contenu complet le dépasse,
   **Then** la carte est réduite par priorités explicites et déterministes (jamais de
   coupe silencieuse : la carte indique ce qui a été omis et comment l'obtenir).
3. **Given** deux exports successifs du même dépôt, **Then** ils sont identiques octet
   pour octet.
4. **Given** un monorepo, **When** l'export est demandé, **Then** la carte couvre les
   sous-projets et leurs liens inter-services.

---

### User Story 2 - Interroger le graphe depuis un assistant IA (serveur local) (Priority: P2)

L'utilisateur branche son assistant (Claude Code, Cursor…) sur un serveur local
CodeAtlas exposant le graphe de code via le protocole standard des outils d'IA (MCP).
L'assistant peut chercher un symbole, obtenir l'API d'un module, remonter appelants et
appelés, connaître la couche d'un élément, lister le code mort — sans que le code ne
quitte la machine et sans réponse inventée : chaque réponse vient du graphe.

**Why this priority**: transforme la carte statique en dialogue outillé — le mode
d'usage dominant des assistants en 2026 ; dépend du graphe (déjà là) et des choix de
format de la story 1.

**Independent Test**: démarrer le serveur sur le corpus, appeler chaque outil exposé
avec des cas connus (symbole existant, inexistant, ambigu) et vérifier des réponses
exactes, déterministes et issues du graphe uniquement.

**Acceptance Scenarios**:

1. **Given** le serveur démarré sur un dépôt, **When** l'assistant cherche un symbole
   par nom, **Then** il reçoit les correspondances exactes avec fichier, ligne,
   signature et documentation — ou une liste vide, jamais une invention.
2. **Given** un symbole, **When** l'assistant demande ses appelants et appelés,
   **Then** la réponse distingue les liens sûrs des liens incertains.
3. **Given** le serveur en fonctionnement, **Then** aucun octet ne sort de la machine
   (aucun appel réseau sortant), vérifiable en environnement isolé.

---

### User Story 3 - Analyse d'impact d'un changement (Priority: P2)

Avant de modifier un fichier ou un symbole, le développeur (ou son assistant via le
serveur) demande « qu'est-ce que ça touche ? » : CodeAtlas remonte le rayon de
propagation — qui appelle, qui importe, quels points d'entrée mènent ici — avec la
profondeur en paramètre.

**Why this priority**: le complément naturel du diff architectural (feature 002) et
l'outil le plus demandé par les assistants ; s'appuie uniquement sur le graphe
existant.

**Independent Test**: sur le corpus, l'impact d'un symbole feuille connu remonte
exactement les chaînes d'appel/import attendues jusqu'à la profondeur demandée.

**Acceptance Scenarios**:

1. **Given** un symbole du corpus, **When** l'impact est demandé à profondeur N,
   **Then** la réponse liste les éléments affectés par niveau (appelants directs,
   puis indirects…), avec les points d'entrée atteints marqués comme tels.
2. **Given** un fichier, **When** l'impact est demandé, **Then** l'analyse couvre tous
   les symboles définis dans ce fichier.
3. **Given** un symbole sans référence entrante, **Then** la réponse est explicitement
   vide (et cohérente avec la détection de code mort).

---

### User Story 4 - Parcours de lecture guidé (Priority: P3)

Pour l'onboarding, CodeAtlas génère un « parcours de lecture » ordonné et déterministe :
par quels points d'entrée commencer, puis quelles couches et modules lire dans quel
ordre (des dépendants vers les dépendances), avec les pages de doc correspondantes.
Inclus dans le site et dans la carte exportée.

**Why this priority**: forte valeur d'onboarding (inspirée des « tours » 
d'Understand-Anything) mais dérivable entièrement des données existantes.

**Independent Test**: sur le corpus en couches, le parcours commence par les points
d'entrée API, descend domaine puis infrastructure, et deux générations sont identiques.

**Acceptance Scenarios**:

1. **Given** un dépôt avec couches et points d'entrée détectés, **When** le parcours
   est généré, **Then** l'ordre proposé va des points d'entrée vers les couches basses
   et chaque étape référence sa page de documentation.

---

### Edge Cases

- Dépôt sans documentation interne : la carte reste utile (structure + signatures) ;
  les résumés absents ne sont jamais inventés.
- Budget de carte trop petit pour l'essentiel : la carte le dit explicitement et
  liste ce qui a été omis (jamais de coupe silencieuse).
- Symbole ambigu dans une requête serveur : liste des candidats, jamais un choix
  silencieux.
- Serveur interrogé pendant que le code change : les réponses viennent de l'analyse
  chargée, l'horodatage d'analyse est exposé ; un rechargement est possible à la
  demande.
- Requête sur un très gros graphe : réponses bornées (pagination/limites explicites).
- Aucun LLM disponible chez l'utilisateur : la carte et le parcours restent lisibles
  par un humain (markdown propre) — la feature ne DÉPEND d'aucune IA.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT exporter une carte du dépôt en formats texte lisibles
  machine ET humain (au minimum : markdown compact, et le graphe structuré existant),
  dérivée exclusivement du graphe de code.
- **FR-002**: La carte DOIT respecter un budget de taille configurable via une
  priorisation déterministe documentée (points d'entrée et APIs publiques d'abord),
  et signaler explicitement toute omission.
- **FR-003**: Les exports DOIVENT être déterministes octet pour octet et exempts
  d'horodatages.
- **FR-004**: Le système DOIT proposer un serveur local conforme au protocole standard
  d'outillage des assistants IA (MCP), exposant au minimum : recherche de symbole,
  API d'un module, appelants/appelés (certitude distinguée), couche/architecture,
  code mort, analyse d'impact.
- **FR-005**: Le serveur NE DOIT émettre aucun appel réseau sortant ; toutes les
  réponses proviennent du graphe de code — jamais de contenu inventé.
- **FR-006**: Le système DOIT fournir l'analyse d'impact d'un fichier ou d'un symbole
  (rayon de propagation par niveaux via appels et imports, profondeur paramétrable,
  points d'entrée atteints marqués).
- **FR-007**: Le système DOIT générer un parcours de lecture ordonné et déterministe
  (points d'entrée → couches basses) intégré au site et à la carte.
- **FR-008**: Toutes les capacités DOIVENT être exposées par la bibliothèque
  (`codeatlas.api`), la CLI et le serveur n'étant que des façades.
- **FR-009**: L'installation du serveur DOIT être optionnelle (extra dédié) : le cœur
  reste sans dépendance nouvelle.

### Key Entities

- **RepoMap** : carte exportée — sections ordonnées, budget, liste des omissions.
- **ImpactReport** : résultat d'analyse d'impact — niveaux successifs d'éléments
  affectés, points d'entrée atteints, certitude des liens.
- **ReadingTour** : parcours de lecture — étapes ordonnées référençant éléments et
  pages de doc.
- **Outil serveur** : contrat de chaque requête exposée à l'assistant — entrée,
  sortie structurée, limites.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sur le corpus, 100 % des APIs publiques figurent dans la carte quand le
  budget le permet ; sous budget contraint, la priorisation documentée est respectée
  et les omissions sont listées.
- **SC-002**: Deux exports successifs (carte, parcours) sont identiques octet pour
  octet ; les réponses du serveur sont déterministes à requête identique.
- **SC-003**: Le serveur répond à chaque outil en moins d'une seconde sur un dépôt de
  50 000 lignes, sans aucun appel réseau sortant (vérifié en environnement isolé).
- **SC-004**: L'analyse d'impact du corpus retrouve 100 % des chaînes d'appel
  attendues introduites volontairement, sans faux élément.
- **SC-005**: Un assistant IA standard (compatible MCP) découvre et appelle les outils
  du serveur sans configuration au-delà de la commande de lancement.

## Assumptions

- MCP est le protocole d'intégration retenu (standard de fait des assistants en
  2026 : Claude Code, Cursor, Copilot, etc.) ; le choix de la bibliothèque serveur
  relève du plan.
- La carte vit par défaut dans un répertoire versionnable du dépôt (à la manière du
  `.ua/` d'Understand-Anything) ; emplacement configurable.
- Le budget de carte s'exprime en caractères (approximation documentée des tokens,
  indépendante de tout fournisseur d'IA).
- Les « résumés » de la carte sont les premières lignes de documentation existantes —
  jamais de texte généré : s'il n'y a pas de doc, la carte montre la signature seule.
- La fraîcheur du serveur est celle de l'analyse chargée (rechargement à la demande) ;
  la surveillance continue du système de fichiers est hors périmètre v1.
- Le parcours de lecture est structurel (topologie + couches) ; toute narration
  pédagogique reste du ressort de l'assistant IA de l'utilisateur.
