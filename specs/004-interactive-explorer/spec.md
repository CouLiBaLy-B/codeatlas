# Feature Specification: Explorateur interactif — la documentation devient une interface

**Feature Branch**: `004-interactive-explorer`

**Created**: 2026-07-18

**Status**: Implemented (2026-07-18)

**Input**: User description: "Considérer CodeAtlas comme la base d'un projet plus
ambitieux : rendre le projet plus complet, avec plus d'interactivité. La documentation
générée ne doit plus être seulement lisible, elle doit être explorable — on navigue
dans l'architecture comme dans une carte, on cherche, on filtre, on creuse."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explorer le graphe d'architecture comme une carte (Priority: P1)

Un développeur ouvre la documentation générée et, au lieu d'un diagramme figé, dispose
d'une vue explorable du graphe de code : il se déplace (zoom, panoramique), clique sur
un module pour voir sa fiche (API, métriques, dépendances), déplie ou replie le
voisinage d'un nœud, filtre par langage, couche architecturale ou sous-projet. La vue
reste utilisable sur un vrai dépôt (centaines de modules) grâce à des niveaux de
détail : on part d'une vue agrégée (sous-projets, couches) et on descend
progressivement vers les modules et symboles.

**Why this priority**: c'est le cœur de la promesse « plus d'interactivité » — la
valeur différenciante de la feature. Les diagrammes statiques existants montrent ;
l'explorateur permet de comprendre en manipulant.

**Independent Test**: générer la documentation du corpus monorepo-demo, ouvrir la vue
explorable, vérifier qu'on peut zoomer, cliquer un module et atteindre sa fiche,
filtrer par couche, et que la vue agrégée initiale se déplie jusqu'aux modules.

**Acceptance Scenarios**:

1. **Given** un site généré, **When** l'utilisateur ouvre la vue d'architecture,
   **Then** il voit une vue agrégée (sous-projets/couches) qu'il peut zoomer et
   déplacer sans rechargement de page.
2. **Given** la vue explorable, **When** l'utilisateur clique sur un nœud, **Then**
   une fiche s'affiche (nom, type, langage, couche, métriques clés, dépendances
   entrantes/sortantes) avec un lien vers la page de documentation détaillée.
3. **Given** la vue explorable, **When** l'utilisateur applique un filtre (langage,
   couche, sous-projet), **Then** seuls les éléments correspondants et leurs liens
   restent visibles, et le filtre est reflété dans l'adresse de la page (partageable).
4. **Given** un dépôt de plusieurs centaines de modules, **When** la vue s'ouvre,
   **Then** elle affiche d'abord un niveau agrégé lisible et permet de déplier
   progressivement, sans jamais figer le navigateur.
5. **Given** un navigateur sans scripts actifs, **When** la page s'ouvre, **Then** un
   diagramme statique équivalent au comportement actuel reste affiché (repli honnête).

---

### User Story 2 - Trouver n'importe quel symbole instantanément (Priority: P2)

Depuis n'importe quelle page du site, le développeur tape quelques caractères et
obtient instantanément les symboles correspondants (modules, classes, fonctions) avec
signature, langage et emplacement ; il navigue au clavier et atteint la fiche du
symbole en un geste. La recherche fonctionne entièrement hors-ligne, sur le contenu
réellement analysé — jamais de résultat inventé.

**Why this priority**: la recherche est le geste d'entrée le plus fréquent dans une
documentation ; elle démultiplie la valeur de l'explorateur (story 1) en offrant un
point d'entrée direct vers chaque fiche.

**Independent Test**: générer le site du corpus python-demo, saisir un nom de classe
connu, vérifier que le symbole apparaît avec sa signature et que la sélection mène à
sa fiche ; saisir un nom inexistant et vérifier une réponse vide explicite.

**Acceptance Scenarios**:

1. **Given** un site généré, **When** l'utilisateur saisit un fragment de nom, **Then**
   les symboles correspondants s'affichent classés par pertinence (préfixe exact avant
   correspondance partielle), avec type, signature et module d'origine.
2. **Given** des résultats affichés, **When** l'utilisateur navigue au clavier et
   valide, **Then** il atteint la fiche du symbole sélectionné.
3. **Given** une saisie sans correspondance, **Then** l'interface l'indique clairement
   (aucun résultat), sans suggestion approximative trompeuse.
4. **Given** le site ouvert sans aucun accès réseau, **Then** la recherche fonctionne
   à l'identique.

---

### User Story 3 - Atelier local : voir la documentation vivre avec le code (Priority: P2)

Le développeur lance un mode « atelier » local : la documentation est servie sur sa
machine et se met à jour quand il modifie son code. Il garde le site ouvert à côté de
son éditeur ; à chaque sauvegarde, seuls les éléments impactés sont réanalysés et le
navigateur reflète le changement en quelques secondes. Une modification invalide ne
casse jamais la session : l'élément fautif est signalé et le reste du site reste servi.

**Why this priority**: transforme CodeAtlas d'un générateur « one-shot » en compagnon
de développement quotidien — la boucle de feedback qui rend l'interactivité utile au
jour le jour. Dépend des vues des stories 1 et 2 pour prendre toute sa valeur.

**Independent Test**: lancer le mode atelier sur le corpus python-demo, modifier la
signature d'une fonction, vérifier que la page du module reflète le changement en
moins de cinq secondes ; introduire une erreur de syntaxe et vérifier que le site
reste servi avec un avertissement visible.

**Acceptance Scenarios**:

1. **Given** le mode atelier démarré, **When** un fichier source est modifié et
   sauvegardé, **Then** la documentation impactée est régénérée et visible dans le
   navigateur en quelques secondes, sans relancer la commande.
2. **Given** une modification introduisant une syntaxe invalide, **Then** la session
   continue : l'élément est signalé comme ignoré (avertissement structuré) et le reste
   de la documentation reste servi.
3. **Given** plusieurs sauvegardes rapprochées, **Then** les régénérations sont
   regroupées et la dernière version du code fait foi (pas de file d'attente qui
   s'accumule).
4. **Given** le mode atelier, **Then** le service n'écoute que sur la machine locale
   et n'émet aucune requête vers l'extérieur.

---

### User Story 4 - Tableau de bord santé explorable (Priority: P3)

Le responsable technique ouvre le tableau de bord de santé du code : les métriques
(complexité, taille, couplage, code mort, dette de documentation) sont présentées en
tableaux triables et filtrables et en vues proportionnelles (les zones les plus
préoccupantes sautent aux yeux). Chaque ligne ou zone est cliquable et mène à la fiche
de l'élément concerné.

**Why this priority**: valorise des métriques déjà calculées en les rendant
actionnables ; utile mais moins différenciant que l'explorateur et la recherche.

**Independent Test**: générer le site du corpus monorepo-demo, trier le tableau par
complexité décroissante, vérifier l'ordre ; cliquer la première ligne et atteindre la
fiche de l'élément.

**Acceptance Scenarios**:

1. **Given** le tableau de bord, **When** l'utilisateur trie par une métrique, **Then**
   les lignes se réordonnent sans rechargement et l'ordre est exact.
2. **Given** une vue proportionnelle des métriques, **When** l'utilisateur clique une
   zone, **Then** il atteint la fiche de l'élément correspondant.
3. **Given** des fichiers ignorés lors de l'analyse, **Then** le tableau de bord les
   présente avec leur motif, au même niveau de visibilité que les métriques.

---

### User Story 5 - De la fiche au code source (Priority: P3)

Depuis la fiche d'un symbole, le développeur consulte l'extrait de source correspondant
(délimité et mis en évidence) et rebondit d'un clic vers les appelants, les appelés et
les définitions liées — la documentation et le code deviennent un seul espace de
navigation.

**Why this priority**: complète la boucle d'exploration (graphe → fiche → source →
graphe) ; s'appuie entièrement sur les données déjà présentes dans le graphe de code.

**Independent Test**: ouvrir la fiche d'une fonction du corpus python-demo, vérifier
que l'extrait de source affiché correspond aux lignes de sa définition et que les
liens appelants/appelés mènent aux bonnes fiches.

**Acceptance Scenarios**:

1. **Given** la fiche d'un symbole, **When** l'utilisateur ouvre la vue source,
   **Then** l'extrait affiché correspond exactement à l'emplacement (fichier, lignes)
   connu du graphe.
2. **Given** la fiche d'une fonction, **When** l'utilisateur clique un appelant ou un
   appelé, **Then** il atteint la fiche de ce symbole ; les liens incertains sont
   visuellement distingués des liens sûrs.
3. **Given** un symbole dont le fichier source n'a pas pu être lu ou inclus, **Then**
   la fiche l'indique explicitement au lieu d'afficher une vue vide.

---

### Edge Cases

- Dépôt très volumineux (des milliers de nœuds) : la vue explorable doit rester
  fluide via l'agrégation par niveaux — jamais de rendu brut de tout le graphe.
- Scripts désactivés ou navigateur ancien : chaque vue interactive a un repli statique
  équivalent au rendu actuel (diagrammes, tableaux simples).
- Site consulté depuis le système de fichiers (sans serveur) : recherche et
  explorateur doivent fonctionner, ou à défaut afficher le repli statique avec une
  explication — jamais une page cassée silencieuse.
- Symboles homonymes (même nom dans plusieurs modules/langages) : la recherche et les
  fiches les distinguent sans ambiguïté (module, langage, chemin).
- Mode atelier : suppression ou renommage de fichiers pendant la session ; arrêt
  propre ; port déjà occupé (message clair, pas de crash).
- Deux générations successives du même dépôt : tous les artefacts interactifs (données
  de vues, index de recherche) doivent être identiques octet pour octet.
- Fichiers non analysables : ils n'interrompent ni la génération ni le mode atelier et
  restent visibles dans le tableau de bord avec leur motif.

## Requirements *(mandatory)*

### Functional Requirements

**Explorateur de graphe**

- **FR-001**: Le site généré DOIT proposer une vue d'architecture explorable :
  déplacement, zoom et sélection de nœuds sans rechargement de page.
- **FR-002**: La vue DOIT s'ouvrir sur un niveau agrégé (sous-projets, couches) et
  permettre de déplier progressivement jusqu'aux modules ; le niveau symbole est
  accessible depuis la fiche d'un module.
- **FR-003**: La sélection d'un nœud DOIT afficher une fiche : identité (nom, type,
  langage, couche, sous-projet), métriques clés, dépendances entrantes et sortantes,
  et lien vers la page de documentation détaillée.
- **FR-004**: La vue DOIT offrir des filtres par langage, couche architecturale et
  sous-projet, combinables, dont l'état est encodé dans l'adresse de la page.
- **FR-005**: Chaque vue interactive DOIT avoir un repli statique équivalent au rendu
  actuel, affiché quand les scripts ne sont pas disponibles.

**Recherche**

- **FR-006**: Le site DOIT offrir une recherche de symboles (modules, types,
  fonctions) accessible depuis toute page, fonctionnant sans aucun accès réseau.
- **FR-007**: Les résultats DOIVENT présenter type, signature, module d'origine et
  langage, être classés par pertinence déterministe (préfixe exact avant partiel, puis
  ordre lexicographique) et être navigables au clavier.
- **FR-008**: Une recherche sans correspondance DOIT l'indiquer explicitement ; la
  recherche ne DOIT jamais présenter un résultat absent du graphe de code.

**Mode atelier**

- **FR-009**: Une commande DOIT servir la documentation localement et régénérer les
  éléments impactés à chaque modification de fichier source, la mise à jour étant
  visible dans le navigateur sans action manuelle.
- **FR-010**: La régénération DOIT être incrémentale : seuls les éléments dont
  l'analyse dépend des fichiers modifiés sont recalculés ; des modifications
  rapprochées sont regroupées.
- **FR-011**: En mode atelier, un fichier devenu non analysable DOIT être signalé
  (avertissement structuré et visible dans le site) sans interrompre la session ni le
  service du reste de la documentation.
- **FR-012**: Le service local ne DOIT écouter que sur l'interface locale, n'émettre
  aucune requête sortante, et refuser proprement de démarrer si le port est occupé.

**Tableau de bord**

- **FR-013**: Le tableau de bord DOIT présenter les métriques de santé en tableaux
  triables et filtrables côté client, chaque ligne menant à la fiche de l'élément.
- **FR-014**: Le tableau de bord DOIT inclure une vue proportionnelle cliquable,
  dimensionnée par une métrique choisie dans la configuration du projet (avec un
  repli lisible quand cette métrique est nulle partout).
- **FR-015**: Les fichiers ignorés et avertissements d'analyse DOIVENT être présentés
  dans le tableau de bord avec leur motif.

**Navigation source**

- **FR-016**: La fiche d'un symbole DOIT donner accès à l'extrait de source de sa
  définition (fichier et lignes exacts), avec mise en évidence de l'élément.
- **FR-017**: Les appelants et appelés affichés sur une fiche DOIVENT être cliquables
  et distinguer visuellement les liens sûrs des liens incertains.

**Transversal (constitution)**

- **FR-018**: Tous les artefacts générés (pages, données des vues, index de recherche,
  ressources embarquées) DOIVENT être déterministes : deux générations du même dépôt
  produisent des sorties identiques octet pour octet.
- **FR-019**: Le site généré ne DOIT référencer aucune ressource externe : toutes les
  ressources nécessaires aux vues interactives sont embarquées dans le site.
- **FR-020**: Les vues interactives ne DOIVENT consommer que des données issues de
  l'IR (jamais d'analyse spécifique à un langage côté rendu) ; ajouter un langage ne
  DOIT demander aucune modification des vues.
- **FR-021**: Les capacités du mode atelier et de la génération des vues DOIVENT être
  exposées d'abord comme API de bibliothèque, la CLI restant une façade fine.

### Key Entities

- **Vue d'architecture (données d'exploration)** : représentation navigable du graphe
  de code par niveaux (sous-projet → couche → module), dérivée exclusivement de l'IR ;
  porte nœuds, arêtes, agrégats et attributs de filtrage.
- **Fiche de symbole** : carte d'identité d'un élément (module, type, fonction) —
  identité, signature, métriques, relations (appels, imports), emplacement source.
- **Index de recherche** : liste déterministe des symboles interrogeable côté client ;
  entrées portant nom, type, signature, module, langage et cible de navigation.
- **Session d'atelier** : cycle de vie du service local — état de l'analyse,
  dépendances fichiers → éléments impactés, avertissements courants.
- **Avertissement d'analyse** : signalement structuré (fichier, motif, portée) exposé
  dans le tableau de bord et en mode atelier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Depuis n'importe quelle page, un utilisateur trouve et atteint la fiche
  d'un symbole dont il connaît le nom en moins de 5 secondes.
- **SC-002**: Sur un dépôt de ~50 000 lignes, chaque interaction de l'explorateur
  (zoom, filtre, sélection, dépliage) répond sans latence perceptible (< 200 ms).
- **SC-003**: Le site généré est intégralement fonctionnel sans aucun accès réseau ;
  aucune requête externe n'est émise à la consultation.
- **SC-004**: Deux générations successives du même dépôt produisent des artefacts
  identiques octet pour octet (vérifié en CI sur les corpus d'exemple).
- **SC-005**: La génération avec vues interactives ne dépasse pas de plus de 20 % la
  durée de génération actuelle sur le même corpus, et reste sous le budget
  constitutionnel (50 000 lignes en moins de 30 secondes).
- **SC-006**: En mode atelier, une modification de source est visible dans le
  navigateur en moins de 5 secondes sur les corpus d'exemple.
- **SC-007**: Sans scripts actifs, 100 % des contenus (diagrammes, tableaux, fiches)
  restent consultables sous forme statique.
- **SC-008**: Sur le corpus monorepo-demo, un nouvel arrivant identifie les
  sous-projets, leurs dépendances mutuelles et les trois modules les plus complexes en
  moins de 3 minutes, sans lire le code.

## Assumptions

- L'interactivité vit entièrement dans le site généré (consultation locale ou
  hébergement statique) : aucun service en ligne, aucun compte, aucune télémétrie —
  le mode atelier n'est qu'une convenance locale de développement.
- Les navigateurs cibles sont les navigateurs récents ; les environnements sans
  scripts reçoivent le repli statique (comportement actuel), considéré comme
  acceptable et non comme une régression.
- Les vues interactives se nourrissent exclusivement du graphe de code existant (IR)
  et des métriques déjà calculées par les features 001-003 ; aucune nouvelle analyse
  de langage n'est requise.
- Le déterminisme s'applique aux artefacts générés ; le mode atelier (processus
  vivant) doit converger vers ces mêmes artefacts à code source identique.
- Les corpus d'exemple versionnés (python-demo, java-demo, monorepo-demo) restent la
  base de validation ; les seuils de fluidité sont mesurés sur une machine de
  développement standard.
- L'affichage d'extraits de source dans le site est acceptable (la documentation est
  générée par et pour les détenteurs du code) ; une option d'exclusion existe pour
  les cas sensibles.
