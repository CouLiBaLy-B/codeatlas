# Feature Specification: Diff architectural — l'architecture sous contrôle de version

**Feature Branch**: `002-architectural-diff`

**Created**: 2026-07-18

**Status**: Draft

**Input**: User description: "Puisque les sorties de CodeAtlas sont déterministes, deux
états du dépôt sont comparables. Fournir un diff architectural : quels cycles,
violations de couches, APIs publiques, liens incertains, métriques sont apparus ou ont
disparu entre une base de référence et l'état courant — en local, en gate CI, et en
commentaire de pull request. Personne ne le fait en multi-langage."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comparer l'état courant à une référence (Priority: P1)

Un développeur capture une référence architecturale de son dépôt (« baseline »,
fichier versionnable), travaille, puis demande le diff : CodeAtlas liste ce qui est
**apparu** et ce qui a **disparu** — cycles de packages, violations de couches, APIs
publiques, liens d'appel incertains, symboles morts probables — et le delta des
métriques globales (couverture de doc, symboles critiques).

**Why this priority**: c'est le socle : sans capture de référence ni moteur de
comparaison, rien d'autre n'existe. Utilisable seul dès le premier jour
(« qu'est-ce que ma branche change à l'architecture ? »).

**Independent Test**: sur le corpus python-demo, capturer une baseline, introduire un
cycle et une fonction publique non documentée, relancer le diff : les deux apparitions
sont listées, rien d'autre.

**Acceptance Scenarios**:

1. **Given** une baseline capturée, **When** le dépôt n'a pas changé, **Then** le diff
   est explicitement vide (« aucun changement architectural ») et le code de sortie
   est 0.
2. **Given** une baseline capturée, **When** un nouveau cycle de packages est introduit,
   **Then** le diff le liste comme APPARU avec les packages impliqués et les imports
   qui le matérialisent.
3. **Given** une baseline capturée, **When** une API publique est supprimée, **Then**
   le diff la liste comme DISPARUE (rupture potentielle pour les consommateurs).
4. **Given** deux exécutions du diff sur les mêmes états, **Then** les sorties sont
   identiques octet pour octet.

---

### User Story 2 - Gate CI sur régression architecturale (Priority: P1)

Une équipe branche le diff dans sa CI : le job échoue si le changement introduit une
régression d'une catégorie interdite (nouveau cycle, nouvelle violation de couche,
nouveau lien incertain, API publique supprimée…), chaque catégorie étant activable
dans la configuration.

**Why this priority**: c'est la promesse produit (« l'architecture sous contrôle de
version ») ; la valeur en équipe passe par le blocage automatique.

**Independent Test**: baseline sur le corpus, introduction d'un cycle, exécution du
mode gate avec `nouveau cycle interdit` : exit code de régression ; sans la règle :
exit 0.

**Acceptance Scenarios**:

1. **Given** une règle « aucun nouveau cycle », **When** un cycle apparaît, **Then**
   le mode gate sort en échec (code dédié) en nommant la règle violée et les éléments.
2. **Given** aucune règle configurée, **When** le diff n'est pas vide, **Then** le mode
   gate reste en succès (informatif seulement).
3. **Given** une baseline absente, **When** le gate s'exécute, **Then** il crée la
   baseline et sort en succès avec un message explicite (premier lancement jamais
   bloquant).

---

### User Story 3 - Commentaire de pull request (Priority: P2)

Sur GitHub, chaque pull request reçoit (via l'Action CodeAtlas) un commentaire compact
résumant le diff architectural — mis à jour à chaque push de la branche, jamais
dupliqué. Les régressions y sont visuellement distinguées des évolutions neutres.

**Why this priority**: c'est là que le diff devient visible par toute l'équipe au bon
moment (la revue) ; dépend des stories 1 et 2.

**Independent Test**: générer le commentaire markdown depuis un diff connu du corpus et
vérifier son contenu (sections apparitions/disparitions, icônes de sévérité,
marqueur d'idempotence pour la mise à jour).

**Acceptance Scenarios**:

1. **Given** un diff non vide, **When** le rendu « commentaire PR » est demandé,
   **Then** un markdown autonome est produit : résumé chiffré, régressions en tête,
   détails traçables (éléments impliqués), marqueur stable permettant la mise à jour
   du même commentaire.
2. **Given** un diff vide, **When** le rendu est demandé, **Then** le markdown dit
   explicitement « aucun changement architectural » (pas de commentaire silencieux).

---

### User Story 4 - Changelog architectural (Priority: P3)

Le site généré contient une page « Changelog architectural » : l'historique des diffs
capturés version après version (quand l'équipe archive ses baselines), donnant la
trajectoire de l'architecture dans le temps.

**Why this priority**: valeur de long terme, dépend de l'accumulation de baselines.

**Independent Test**: avec deux baselines archivées du corpus, la page liste les deux
entrées dans l'ordre, chacune avec son résumé de changements.

**Acceptance Scenarios**:

1. **Given** des baselines archivées avec étiquettes, **When** le site est généré,
   **Then** la page changelog présente chaque étape avec ses apparitions/disparitions.

---

### Edge Cases

- Baseline absente : jamais bloquant — création + message (US2/AC3).
- Baseline produite par une version incompatible de CodeAtlas (version d'IR
  différente) : erreur d'usage explicite invitant à recapturer, jamais de comparaison
  silencieusement fausse.
- Renommage d'un symbole : v1 le traite honnêtement comme disparition + apparition
  (documenté) ; pas de fausse détection de rupture masquée.
- Dépôt monorepo : le diff couvre aussi les sous-projets et liens inter-services
  (apparition/disparition de sous-projets incluse).
- Très gros diff (refactoring massif) : sortie tronquée avec compte exact et mention
  explicite de la troncature (jamais silencieuse).
- Fichiers inanalysables : les entrées `skipped` apparues/disparues font partie du
  diff (une baisse de couverture d'analyse est une information architecturale).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT capturer une « baseline » : représentation compacte,
  versionnable dans le dépôt et déterministe de l'état architectural (éléments
  publics, cycles, violations, liens incertains, code mort, métriques globales,
  sous-projets), horodatage exclu.
- **FR-002**: Le système DOIT comparer l'état courant à une baseline et produire un
  delta par catégories : apparu / disparu, chaque entrée étant traçable (éléments de
  code impliqués).
- **FR-003**: Le diff DOIT être déterministe : mêmes états comparés → sortie identique
  octet pour octet ; états identiques → diff vide.
- **FR-004**: Le mode gate DOIT échouer avec un code de sortie dédié quand une règle
  de régression configurée est violée (catégories activables individuellement :
  nouveaux cycles, nouvelles violations, nouveaux liens incertains, API publique
  supprimée, chute de couverture de doc au-delà d'un seuil).
- **FR-005**: Une baseline absente ou l'initialisation ne DOIT jamais faire échouer le
  gate (création + succès explicite).
- **FR-006**: Une baseline incompatible (version) DOIT produire une erreur d'usage
  explicite, jamais un résultat silencieusement faux.
- **FR-007**: Le système DOIT produire un rendu « commentaire de PR » : markdown
  autonome, compact, idempotent (marqueur stable de mise à jour), régressions en tête.
- **FR-008**: L'Action GitHub DOIT pouvoir poster/mettre à jour ce commentaire sur la
  PR courante et refléter le gate dans le statut du job.
- **FR-009**: Le site généré DOIT pouvoir inclure une page changelog depuis des
  baselines archivées étiquetées.
- **FR-010**: Toutes les capacités DOIVENT être exposées par la bibliothèque
  (`codeatlas.api`), la CLI n'étant qu'une façade.

### Key Entities

- **Baseline** : instantané architectural versionnable — version de format, résumé des
  éléments publics et détections, métriques ; déterministe, sans horodatage dans le
  contenu comparé.
- **ArchDelta** : résultat de comparaison — par catégorie, listes `apparu` / `disparu`
  d'entrées traçables ; deltas de métriques.
- **RegressionRule** : règle de gate — catégorie surveillée + seuil éventuel + verdict.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sur le corpus de test, l'introduction volontaire d'un cycle, d'une
  violation de couche et d'une suppression d'API publique produit exactement ces trois
  apparitions/disparitions dans le diff — zéro faux positif sur les états inchangés.
- **SC-002**: Deux exécutions du diff sur les mêmes états produisent des sorties
  identiques octet pour octet.
- **SC-003**: Le cycle complet baseline → modification → diff → gate s'exécute en
  moins de 10 secondes sur un dépôt de 50 000 lignes (hors génération du site).
- **SC-004**: Le commentaire de PR tient en moins de 200 lignes de markdown sur les
  diffs du corpus, régressions visibles dans les 10 premières lignes.
- **SC-005**: Un premier lancement sans baseline se termine en succès et crée la
  baseline dans 100 % des cas.

## Assumptions

- La baseline vit par défaut dans le dépôt (fichier versionné) ; son emplacement est
  configurable. C'est l'équipe qui décide quand la rafraîchir (workflow type : mise à
  jour sur la branche principale, comparaison sur les branches).
- La comparaison porte sur les faits architecturaux résumés (pas le graphe complet) :
  suffisant pour les catégories couvertes, et assez compact pour être versionné.
- Le rapprochement entre versions se fait par identifiant stable (nom qualifié) ;
  les renommages produisent disparition + apparition (assumé, documenté).
- Le commentaire de PR est publié par l'Action GitHub (l'API GitHub est disponible
  dans ce contexte CI) ; le cœur reste hors-ligne : il ne fait que produire le
  markdown.
- Les règles de gate par défaut sont toutes désactivées (opt-in explicite).
