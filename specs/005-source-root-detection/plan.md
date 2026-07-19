# Implementation Plan: Détection de la racine des sources

**Branch**: `005-source-root-detection` | **Date**: 2026-07-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-source-root-detection/spec.md`

## Summary

Corriger la résolution des noms de modules Python : déduire statiquement la **racine
d'import** (premier ancêtre sans `__init__.py`) et nommer les modules d'après elle, au
lieu du chemin relatif à la racine analysée. Restaure les arêtes d'import — donc
dépendances de packages, couplage, cycles, couches, repomap, impact et les vues de la
feature 004 — sur les projets en layout `src/` et à package décalé, sans rien changer
au contrat de l'IR ni aux projets déjà corrects. En complément : ignorer les
répertoires de sortie générés (marqueur `.codeatlas-generated` + exclusions par
défaut) pour supprimer les faux sous-projets. Bug de fond exposé par le dogfooding de
la feature 004 (graphe vide, couplage nul sur le propre code de CodeAtlas).

## Technical Context

**Language/Version**: Python ≥ 3.11 (inchangé). **Primary Dependencies**: aucune
nouvelle — détection en Python pur sur les chemins découverts. **Storage**: N/A.
**Testing**: pytest test-first ; nouveau corpus versionné `examples/src-layout-demo/`
et son golden ; tests unitaires de `detect_import_roots` (src/, sous-répertoire,
orphelin, monorepo, repli ambigu) ; validation grandeur nature sur CodeAtlas lui-même
(0 → ~176 imports). **Target Platform**: identique. **Project Type**: bibliothèque +
CLI (inchangé). **Performance Goals**: SC-006 — détection O(nombre de fichiers), aucune
dégradation super-linéaire ; budget 50 k lignes < 30 s tenu. **Constraints**:
constitution I–V ; statique et déterministe (aucune exécution, aucun `sys.path` réel) ;
contrat IR inchangé (FR-009) ; repli sûr non régressif (FR-006).

Décisions détaillées : [research.md](research.md) (R1–R8).

## Constitution Check

| # | Principe | Évaluation | Verdict |
| --- | --- | --- | --- |
| I | Analyse statique déterministe | détection par structure de fichiers (présence d'`__init__.py`), aucun code exécuté, aucun `sys.path` ; résultat trié/stable ; marqueur au contenu statique | ✅ |
| II | Bibliothèque d'abord | `detect_import_roots` / `module_qualname` sont des fonctions pures testables ; aucune surface CLI nouvelle | ✅ |
| III | IR unifiée | seule la VALEUR des qualnames Python change ; ids, arêtes, schéma et adaptateurs des autres langages inchangés (FR-009) | ✅ |
| IV | Tolérance | racine ambiguë → repli sur le comportement actuel, jamais d'échec ni de dégradation nette (FR-006) | ✅ |
| V | Test-first ≥ 80 % | tests de détection et golden `src-layout-demo` écrits avant l'implémentation ; goldens existants figés (non-régression SC-003) | ✅ |

**Re-check post-design** : ✅ — aucune violation, section Complexity Tracking vide.

## Project Structure

### Documentation (this feature)

```text
specs/005-source-root-detection/
├── plan.md              # ce fichier
├── research.md          # décisions R1–R8
├── data-model.md        # racine d'import, qualname, exclusions, marqueur
├── quickstart.md        # 6 scénarios de validation
├── contracts/source-root.md  # module_qualname / detect_import_roots / exclusions
└── tasks.md             # produit par /speckit-tasks
```

### Source Code (repository root)

```text
src/codeatlas/
├── analyzers/
│   ├── python/
│   │   ├── import_root.py    # NOUVEAU — detect_import_roots (pur, déterministe)
│   │   └── analyzer.py       # module_qualname(path, import_root) ; usage à la découverte
│   └── base.py               # discover_files : ignore les répertoires marqués générés
├── config.py                 # DEFAULT_EXCLUDES : + artefacts générés sans ambiguïté
└── site/builder.py           # dépose .codeatlas-generated à la racine du site produit

examples/src-layout-demo/     # NOUVEAU corpus : src/mypkg/… avec imports internes
└── src/mypkg/{__init__,core,util,models/…}.py

tests/
├── unit/test_import_root.py          # détection : src/, sous-répertoire, orphelin, monorepo, repli
├── golden/test_src_layout_golden.py  # graphe du corpus src-layout-demo
└── integration/test_generated_dirs_ignored.py  # marqueur + exclusions (SC-005)
```

**Structure Decision**: la détection vit dans un module dédié `analyzers/python/
import_root.py` (pur, sans I/O au-delà des chemins), consommé par l'analyseur à la
construction des modules — là où le nom qualifié sert à résoudre imports et symboles.
Le marqueur de génération relie proprement `site/` (producteur) et `analyzers/base`
(consommateur) sans couplage de code. Aucun package nouveau : la feature est
chirurgicale et confinée à l'analyseur Python et à deux points d'intégration.

## Complexity Tracking

Aucune violation — section vide.
