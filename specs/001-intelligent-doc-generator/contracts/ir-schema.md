# Contract: IR — Graphe de code

Contrat **central** du produit (constitution III) : les analyseurs le produisent, tout
l'aval le consomme. Toute évolution est versionnée (`ir_version`) et
rétro-compatible au sein d'une version majeure de CodeAtlas.

## Types de nœuds (`NodeKind`)

| Kind | Description | Champs spécifiques |
| --- | --- | --- |
| `package` | package/répertoire de modules | — |
| `module` | fichier source | `loc` |
| `class` | classe | `modifiers` (`abstract`, `exported`…) |
| `interface` | interface/protocol/ABC | — |
| `enum` | énumération | — |
| `function` | fonction libre | `signature`, `complexity`, `loc`, `modifiers` (`async`…) |
| `method` | méthode (rattachée à un type) | idem function + `static`/`classmethod` |
| `attribute` | attribut/champ typé | type déclaré si connu |

Champs communs : `id`, `name`, `subproject`, `location {file, line}`, `visibility`,
`doc {raw, summary, format}` (format ∈ `docstring` | `jsdoc` | `javadoc` | `none`).

## Types d'arêtes (`EdgeKind`)

| Kind | Sémantique UML/graphe | Source → Cible |
| --- | --- | --- |
| `inherits` | héritage | class → class |
| `implements` | réalisation | class → interface |
| `composes` | composition (possession forte) | class → class |
| `aggregates` | agrégation | class → class |
| `associates` | association (attribut typé, param) | class → class |
| `imports` | dépendance de module | module → module |
| `calls` | appel résolu | function/method → function/method |
| `references` | usage d'un symbole hors appel | tout → tout |
| `service_dep` | dépendance inter-sous-projets | subproject → subproject |

Champs communs : `source`, `target`, `kind`, `certainty` (`certain` | `inferred`),
`location`.

**Règle de certitude** : une arête est `certain` uniquement si la résolution statique
est non ambiguë (import direct, héritage explicite, appel sur symbole local ou importé
nommément). Duck typing, réflexion, imports dynamiques, dispatch par variable →
`inferred`. Les consommateurs DOIVENT distinguer visuellement les deux (FR-009).

## Règles de construction (imposées aux analyseurs)

1. **Ids stables** : nom qualifié complet préfixé du sous-projet
   (`backend/app.services.user.UserService.create`). Deux exécutions sur le même code
   → mêmes ids.
2. **Chemins** : POSIX, relatifs à la racine analysée. Jamais d'absolu.
3. **Ordre** : les fragments livrent nœuds et arêtes triés ; la fusion préserve l'ordre
   global (tri par id).
4. **Tolérance** : un fichier inanalysable produit une entrée `skipped {path, reason}`,
   jamais une exception qui remonte (constitution IV).
5. **Aucune inférence cachée** : un analyseur n'invente pas de relation sans indice
   syntaxique ; le doute se code `inferred`, pas `certain`.
6. **Complexité** : cyclomatique = 1 + points de décision (if/boucles/case/catch/
   opérateurs logiques court-circuit/ternaires) — même définition pour les 3 langages.

## Sérialisation JSON canonique

`codegraph.to_json()` : objet unique, clés triées, UTF-8, indentation 2, fin de ligne
`\n`, champs vides omis. Sert aux golden files et à l'outillage externe.

```json
{
  "ir_version": 1,
  "root": "…",
  "subprojects": [ { "id": "…", "language": "…", "root": "…", "manifest": "…", "name": "…" } ],
  "nodes": [ { "id": "…", "kind": "class", "…": "…" } ],
  "edges": [ { "source": "…", "target": "…", "kind": "inherits", "certainty": "certain" } ],
  "skipped": [ { "path": "…", "reason": "…" } ]
}
```

## Ce que l'IR ne contient PAS (v1)

- Corps des fonctions (seuls les faits extraits en sont dérivés).
- Types résolus par inférence profonde (seulement les annotations déclarées).
- Résultats des insights (métriques agrégées, détections) : calculés à la demande sur
  l'IR, rattachés mais non sérialisés dans `to_json()` de base.
