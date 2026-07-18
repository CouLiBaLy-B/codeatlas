# Quickstart: Explorateur interactif — validation de bout en bout

**Feature**: 004-interactive-explorer

Prérequis : `uv sync` (ou `pip install -e .`), corpus d'exemple du repo
(`examples/monorepo-demo`, `examples/python-demo`).

## 1. Génération avec vues interactives (US1, US2, US4, US5)

```bash
codeatlas build examples/monorepo-demo --out /tmp/atlas-demo
```

Attendu :
- `site/assets/js/` contient le vendor épinglé et les scripts maison ;
  `site/assets/data/atlas-{graph,search,dashboard}.js` présents.
- Ouvrir `architecture/` dans un navigateur : vue agrégée (sous-projets), zoom/pan,
  clic sur un nœud → fiche latérale, filtre par couche reflété dans l'URL (`#…`).
- Barre de recherche : taper un nom de classe du corpus → résultat avec signature,
  Entrée → fiche du symbole. Terme inexistant → « aucun résultat ».
- Tableau de bord : tri par complexité décroissante exact ; champ de filtre
  au-dessus de la table (taper un nom de module → seules ses lignes restent) ;
  clic sur une zone de la treemap → fiche du module ; fichiers volontairement
  invalides du corpus listés avec motif.
- Fiche d'une fonction : extrait de source aux lignes exactes, appelants/appelés
  cliquables, liens incertains distingués.

## 2. Repli sans scripts (FR-005, SC-007)

Recharger les mêmes pages avec JavaScript désactivé. Attendu : diagrammes Mermaid
statiques et tables simples affichés, aucune zone vide ni erreur visible.

## 3. Consultation `file://` (edge case)

Ouvrir `/tmp/atlas-demo/site/index.html` directement (sans serveur). Attendu :
explorateur et recherche fonctionnels (données chargées en `<script src>`), aucune
requête réseau (vérifiable onglet Réseau : uniquement des URLs `file://`).

## 4. Déterminisme (FR-018, SC-004)

```bash
codeatlas build examples/monorepo-demo --out /tmp/atlas-a
codeatlas build examples/monorepo-demo --out /tmp/atlas-b
diff -r /tmp/atlas-a /tmp/atlas-b && echo OK
```

Attendu : `OK` (aucune différence, y compris `atlas-data-*.js` et SVG treemap).

## 5. Mode atelier (US3)

```bash
codeatlas serve examples/python-demo --json &
```

1. Ouvrir `http://127.0.0.1:8321` — site complet servi.
2. Modifier la signature d'une fonction du corpus, sauvegarder : événement `reload`
   sur stdout, page du module mise à jour dans le navigateur en < 5 s (SC-006).
3. Introduire une erreur de syntaxe : événement `warning`, session toujours vivante,
   avertissement visible dans le tableau de bord servi.
4. Corriger l'erreur : l'avertissement disparaît au cycle suivant.
5. Relancer `codeatlas serve` sur le même port pendant que le premier tourne :
   message clair, code retour `4`.
6. Ctrl-C : arrêt propre, code retour `0`. Restaurer le corpus (`git checkout`).

## 6. Équivalence atelier ↔ build à froid (invariant de convergence)

Après la séquence 5 (corpus restauré), comparer le site servi (répertoire de travail
de la session) à un `codeatlas build` à froid : `diff -r` vide.

## 7. Suite de tests

```bash
uv run pytest                        # unit + golden + integration, couverture ≥ 80 %
UPDATE_GOLDEN=1 uv run pytest tests/golden   # après changement volontaire de rendu
```

Goldens ajoutés : `atlas-graph.js` / `atlas-search.js` / `atlas-dashboard.js` et
treemap SVG sur les corpus ; relire le diff avant commit.

## 8. Performance (SC-002, SC-005)

```bash
time codeatlas build <repo-50k-lignes> --out /tmp/atlas-perf   # < 30 s, ≤ +20 % vs --no-explorer
time codeatlas build <repo-50k-lignes> --no-explorer --out /tmp/atlas-base
```

Fluidité : sur `/tmp/atlas-perf`, vérifier zoom/filtre/dépliage sans latence
perceptible (< 200 ms par interaction).
