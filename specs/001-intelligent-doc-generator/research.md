# Research: CodeAtlas — Générateur de documentation intelligente

**Date**: 2026-07-17 | **Feature**: [spec.md](spec.md)

Chaque décision suit le format : Décision / Rationale / Alternatives considérées.

## R1. Parsing multi-langage

**Décision**: Python via le module `ast` de la bibliothèque standard (brique adaptée de
gendoc). JavaScript/TypeScript et Java via **tree-sitter** avec les bindings
`tree-sitter` (py-tree-sitter) et les packages de grammaires officiels PyPI
(`tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-java`), installés en
extras (`codeatlas[javascript]`, `codeatlas[java]`).

**Rationale**: py-tree-sitter et les grammaires officielles publient des wheels
précompilées pour toutes les plateformes majeures — aucun compilateur, Node.js ou JDK
requis chez l'utilisateur (contrainte constitutionnelle). Pour Python, `ast` est plus
riche que tree-sitter (résolution plus fine, docstrings natives) et le code de gendoc
est éprouvé.

**Alternatives considérées**:
- Compilateur TypeScript officiel (précision maximale sur les types) — rejeté : exige
  Node.js chez l'utilisateur.
- `tree-sitter-language-pack` / `py-tree-sitter-languages` (toutes grammaires en un
  paquet) — rejeté : dépendance lourde, versions de grammaires non maîtrisées ; on
  préfère épingler chaque grammaire officielle.
- tree-sitter aussi pour Python (uniformité) — rejeté pour v1 : perte de qualité vs
  `ast` + gendoc ; l'IR garantit déjà l'uniformité en aval.

## R2. Représentation intermédiaire (IR)

**Décision**: Graphe de code custom en dataclasses Python figées (nœuds : sous-projet,
module, type, fonction/méthode, attribut ; arêtes typées : héritage, composition,
association, import, appel, dépendance inter-services), chaque arête portant un niveau
de certitude (`certain` | `inferred`). Identifiants stables = noms qualifiés
(`subproject/package.module.Class.method`). Algorithmes de graphe via **networkx**
(cycles/SCC par Tarjan, atteignabilité, tri topologique), avec itération triée pour le
déterminisme. Export JSON canonique de l'IR (clés triées) pour debug et outillage.

**Rationale**: le contrat IR est LE point d'extension du produit (constitution III) —
il doit être possédé par le projet, pas par une lib externe. networkx est pur Python,
éprouvé, et évite de réécrire Tarjan/atteignabilité ; le déterminisme est garanti par
nos conventions d'itération, pas par la lib.

**Alternatives considérées**:
- Modèle relationnel SQLite — rejeté v1 : complexité sans besoin de persistance.
- Graphe maison sans networkx — rejeté : réécrire SCC/atteignabilité testées n'apporte
  rien ; networkx reste confiné au module `graph/`.

## R3. Référence API : générée depuis l'IR, pas mkdocstrings

**Décision**: Les pages de référence API sont générées par nos templates Jinja2 depuis
l'IR (signatures + docstrings/JSDoc/Javadoc extraites par les analyseurs).
**mkdocstrings n'est pas utilisé** (déviation par rapport à gendoc).

**Rationale**: mkdocstrings ne couvre que Python et contournerait l'IR, violant la
constitution III (tout l'aval consomme l'IR). Une seule chaîne de rendu pour les trois
langages = cohérence visuelle et testabilité (golden files).

**Alternatives considérées**: mkdocstrings pour Python + templates pour le reste —
rejeté : deux chaînes de rendu, sorties hétérogènes, dépendance à l'import du code
analysé (griffe) contraire à l'analyse purement statique de sources arbitraires.

## R4. Site et rendu Mermaid hors-ligne

**Décision**: Site MkDocs Material généré par CodeAtlas (mkdocs.yml + pages produites).
Diagrammes en blocs Mermaid (SuperFences) rendus côté client, avec **mermaid.min.js
vendorisé dans le package CodeAtlas** et copié dans le site (`extra_javascript` local)
— aucun CDN. Export SVG/PNG optionnel via extra `[svg]`.

**Rationale**: recherche web — l'intégration Mermaid de Material peut dépendre d'un
téléchargement (bundle/CDN) et le rendu hors-ligne a des problèmes connus
(issues #3742/#3781 mkdocs-material). Vendoriser mermaid.js garantit SC-007 (zéro
réseau) et un site consultable hors-ligne. Le rendu client-side évite Node.js à la
génération.

**Alternatives considérées**:
- mermaid-cli pour pré-rendre en SVG — rejeté comme voie principale : requiert
  Node/Chromium chez l'utilisateur.
- Kroki (service de rendu) — rejeté : service réseau, contraire à la constitution I.

## R5. Métriques

**Décision**: Complexité cyclomatique calculée par chaque analyseur pendant le parsing
(comptage des points de décision sur l'AST/CST du langage) et stockée comme attribut du
nœud IR. Taille (LOC/nombre de symboles), couplage (fan-in/fan-out sur les arêtes IR),
couverture de documentation interne (ratio de nœuds publics documentés) et code mort
(atteignabilité + comptage de références) calculés uniquement sur l'IR. Seuils par
défaut inspirés des standards (complexité : sain ≤ 10, à surveiller ≤ 20, critique
> 20), surchargables via configuration.

**Rationale**: la complexité exige le détail syntaxique (donc l'analyseur), le reste
est purement structurel (donc l'IR) — conforme constitution III. Pas de dépendance à
radon/lizard : cohérence inter-langages impossible avec des outils mono-langage.

**Alternatives considérées**: radon (Python only) — rejeté ; lizard (multi-langage)
— rejeté : parseur propre distinct du nôtre = incohérences entre la doc et les
métriques.

## R6. Points d'entrée et graphes d'appels

**Décision**: Résolution d'appels statique best-effort sur l'IR : liaison par nom
qualifié + table des symboles importés ; les appels non résolus (duck typing,
réflexion, imports dynamiques) produisent des arêtes `inferred` ou sont comptés comme
non résolus. Détection des points d'entrée par reconnaisseurs pluggables par
framework : Python (`if __name__ == "__main__"`, Click/Typer/argparse, FastAPI/Flask/
Django routes), JS/TS (Express/Nest/Fastify routes, `main` de package, handlers),
Java (`public static void main`, Spring `@RestController`/`@RequestMapping`, JAX-RS).
Diagrammes de flux Mermaid (flowchart) à profondeur réglable (défaut : 3).

**Rationale**: la précision parfaite d'un call graph statique est indécidable en
langage dynamique ; l'honnêteté (arêtes marquées incertaines — exigence FR-009) prime.
Les reconnaisseurs par framework couvrent les cas à 80 % de valeur.

**Alternatives considérées**: analyse de types complète (pyright-like) — rejetée v1 :
coût énorme ; l'architecture des reconnaisseurs permet d'améliorer la résolution
plus tard sans changer l'IR.

## R7. Détection d'architecture, patterns et code mort

**Décision**: Heuristiques sur l'IR, chaque détection portant ses **indices**
(éléments de code justificatifs) et un niveau de confiance — jamais d'affirmation sans
preuve (FR-013). Couches : convention de nommage des packages (api/routes/views,
domain/core/services, infra/db/adapters) croisée avec la direction des dépendances.
Violations : arête remontant le sens des couches, cycles inter-composants. Patterns v1
: Singleton, Factory, Observer, Adapter, Decorator (signatures structurelles sur l'IR).
Code mort : symboles non atteignables depuis les points d'entrée ET sans référence
entrante, confiance dégradée si le symbole est public/exporté.

**Rationale**: heuristiques transparentes et traçables = confiance de l'utilisateur ;
le corpus d'exemple versionné (SC-008) sert de banc de vérité pour éviter les fausses
détections.

**Alternatives considérées**: ML/embeddings pour la détection — rejeté : non
déterministe, opaque, contraire à la constitution I.

## R8. Monorepo

**Décision**: Détection des sous-projets par manifestes standards (`pyproject.toml`/
`setup.py`, `package.json`, `pom.xml`/`build.gradle[.kts]`), du plus profond au plus
proche de la racine, sans chevauchement. Chaque sous-projet est analysé par son
analyseur ; le graphe inter-services est construit depuis les dépendances déclarées
dans les manifestes + les imports croisés détectés.

**Rationale**: les manifestes sont la source la plus fiable et déterministe ;
l'approche « un sous-projet = un fragment d'IR » s'aligne sur l'entité SubProject de la
spec.

**Alternatives considérées**: configuration manuelle obligatoire des sous-projets —
rejetée : contredit « zéro configuration » (FR-016) ; reste possible en surcharge.

## R9. CLI, configuration, distribution

**Décision**: CLI **Click** + affichage **Rich** (héritage gendoc). Configuration
optionnelle TOML : fichier `codeatlas.toml` ou section `[tool.codeatlas]` de
`pyproject.toml`. Packaging PyPI : cœur minimal (`click`, `rich`, `jinja2`,
`networkx`) + extras `[site]` (mkdocs-material), `[javascript]`, `[java]`, `[svg]`,
méta-extra `[all]`. GitHub Action composite (story P2) qui installe et exécute
`codeatlas build` + publie sur Pages. Commandes : `build` (site complet), `check`
(mode CI à seuils, exit code dédié), `diagram` (diagramme focalisé), avec `--json` pour
les rapports machine.

**Rationale**: continuité gendoc, TOML natif (tomllib en 3.11+), extras = installation
minimale par défaut, exit codes distincts pour la CI (FR-018).

**Alternatives considérées**: Typer (sucre au-dessus de Click) — rejeté : Click nu
suffit et réduit les couches ; YAML pour la config — rejeté : TOML natif stdlib.

## R10. Déterminisme et stratégie de tests

**Décision**: Conventions imposées : itérations et sorties systématiquement triées
(chemins POSIX, noms qualifiés), aucun horodatage/UUID/aléa dans les artefacts, IDs
stables. Tests : pytest + pytest-cov (seuil 80 % en CI), **golden files** versionnés
pour les rendus (Mermaid, pages, JSON IR), test d'intégration « double exécution →
diff binaire vide », test « zéro réseau » (socket bloquée pendant la génération),
corpus d'exemples par langage incluant les cas volontaires (cycles, patterns, code
mort, fichier invalide). Lint/typage : ruff + mypy strict.

**Rationale**: rend la constitution I et V vérifiables mécaniquement en CI plutôt que
déclaratives.

**Alternatives considérées**: snapshots via syrupy — rejeté : les golden files bruts
versionnés sont plus lisibles en revue et diffables.

## Sources

- [py-tree-sitter (bindings officiels, wheels précompilées)](https://github.com/tree-sitter/py-tree-sitter)
- [Documentation py-tree-sitter](https://tree-sitter.github.io/py-tree-sitter/)
- [tree-sitter-language-pack (alternative considérée)](https://pypi.org/project/tree-sitter-language-pack/0.7.2/)
- [py-tree-sitter-languages (alternative considérée)](https://github.com/grantjenks/py-tree-sitter-languages)
- [Material for MkDocs — Diagrams (intégration Mermaid)](https://squidfunk.github.io/mkdocs-material/reference/diagrams/)
- [mkdocs-material — Mermaid hors-ligne, issue #3742](https://github.com/squidfunk/mkdocs-material/issues/3742)
- [mkdocs-material — Mermaid sans réseau, issue #3781](https://github.com/squidfunk/mkdocs-material/issues/3781)
- [mkdocs-material — Building for offline usage](https://squidfunk.github.io/mkdocs-material/setup/building-for-offline-usage/)
