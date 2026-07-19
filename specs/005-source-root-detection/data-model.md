# Data Model: Détection de la racine des sources

**Feature**: 005-source-root-detection | **Date**: 2026-07-19

Cette feature ne modifie PAS le contrat de l'IR (FR-009). Elle change la façon dont un
attribut existant — le nom qualifié d'un module, donc l'`id` des nœuds Python et la
résolution des arêtes — est calculé. Aucun champ nouveau dans le graphe.

## Notions

### Racine d'import (interne à l'analyse, non sérialisée)

Répertoire à partir duquel les noms de modules sont calculés pour un fichier donné.
Déduite statiquement (research R1) : premier ancêtre du fichier qui n'est PAS un
package (pas d'`__init__.py`). Peut différer de la racine analysée.

| Cas | Racine analysée | Racine d'import déduite | Nom du module `.../api.py` |
|---|---|---|---|
| Package à la racine (python-demo) | `examples/python-demo` | `examples/python-demo` | `shopdemo.api` (inchangé) |
| Layout `src/` (CodeAtlas) | racine du dépôt | `src/` | `codeatlas.api` (corrigé) |
| Package en sous-répertoire | racine du dépôt | `lib/` | `mypkg.api` |
| Script orphelin | n'importe où | son propre dossier | `script` |

### Nom de module qualifié (déjà dans l'IR — recalculé)

`module_qualname(chemin, racine_import) -> (qualname, is_package)`.
- L'`id` d'un nœud module reste `<subproject>/<qualname>` — seule la valeur de
  `qualname` change pour les dépôts concernés.
- `Location.file` NE change PAS : il reste le chemin relatif au dépôt (les extraits de
  source US5 et la navigation continuent de pointer sur le vrai fichier).

**Invariant de correspondance** : pour tout import interne `from P.M import X` où un
module analysé a le qualname `P.M`, une arête `imports` DOIT exister. C'est cette
correspondance que la feature restaure sur les layouts `src/`.

### Exclusions par défaut (config — étendues)

Liste de motifs de répertoires jamais analysés sauf réintégration explicite. La feature
y ajoute les artefacts générés (research R7) ; la surcharge par configuration reste
possible (les exclusions utilisateur s'ajoutent, elles ne retirent pas — comportement
actuel conservé, sauf réintégration explicite d'un chemin).

### Marqueur de génération

Fichier discret déposé par CodeAtlas à la racine d'un site généré. Contenu statique et
déterministe (aucun horodatage). Sa présence dans un répertoire fait ignorer ce
répertoire à l'analyse. N'apparaît que dans les sorties générées, jamais dans les
sources analysées de l'utilisateur.

## Impact aval (dérivé, non modifié dans son contrat)

Tous ces éléments consomment l'IR et deviennent JUSTES sans changer de forme :
dépendances de packages, couplage (fan-in/fan-out), cycles, couches d'architecture,
carte du dépôt (repomap), analyse d'impact, et les vues interactives de la feature 004
(graphe d'architecture, fiches appelants/appelés). Aucune de ces briques n'est touchée
par le code de cette feature — elles reçoivent simplement des arêtes correctes.
