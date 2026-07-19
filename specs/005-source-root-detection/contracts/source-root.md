# Contracts: Détection de la racine des sources

**Feature**: 005-source-root-detection | **Date**: 2026-07-19

Deux surfaces internes (le comportement observable est le nom des modules et les
arêtes) ; aucune nouvelle commande CLI, aucune option publique nouvelle.

## 1. Dérivation du nom de module (analyzers/python)

```python
def module_qualname(posix_path: str, import_root: str = "") -> tuple[str, bool]:
    """Nom qualifié d'un module et is_package, relatif à `import_root`.

    `import_root` est le préfixe de chemin (POSIX, relatif à la racine analysée) à
    retirer avant de dériver le nom. Vide → comportement historique (nom = chemin).
    Exemples :
      module_qualname("shopdemo/api.py", "")        -> ("shopdemo.api", False)
      module_qualname("src/codeatlas/api.py", "src") -> ("codeatlas.api", False)
      module_qualname("src/codeatlas/__init__.py", "src") -> ("codeatlas", True)
    """
```

```python
def detect_import_roots(paths: Sequence[str]) -> dict[str, str]:
    """Associe à chaque chemin `.py` sa racine d'import déduite (research R1).

    Pur et déterministe : ne dépend que de l'ensemble des chemins fournis (présence
    des `__init__.py`), jamais du système de fichiers réel au-delà des sources
    découvertes, ni d'un ordre d'itération. Repli : chemin dont la racine ne peut être
    tranchée → racine vide (comportement historique)."""
```

- L'analyseur Python utilise `detect_import_roots` sur l'ensemble des fichiers d'un
  sous-projet, puis `module_qualname(path, root)` pour chaque module.
- **Invariant de non-régression** : `detect_import_roots` renvoie une racine vide pour
  tout package déjà à la racine analysée → noms et arêtes strictement inchangés.
- Le contrat de l'IR (ids, arêtes, sérialisation) est inchangé : seule la VALEUR des
  qualnames Python change pour les dépôts en layout `src/` ou à package décalé.

## 2. Exclusions par défaut et marqueur de génération (config + site)

- `DEFAULT_EXCLUDES` (config.py) gagne les motifs d'artefacts générés sans ambiguïté ;
  la résolution actuelle (exclusions utilisateur additives) est conservée.
- La génération de site (site/builder.py) écrit un marqueur `.codeatlas-generated`
  (contenu statique) à la racine du site produit.
- La découverte de fichiers (analyzers/base.py `discover_files`) ignore tout répertoire
  contenant ce marqueur — au même titre que les répertoires exclus.

## 3. Compatibilité

- Aucune commande, option ou clé de configuration nouvelle n'est requise pour bénéficier
  de la correction : elle s'applique par défaut (la justesse est le défaut, research R6).
- Les autres analyseurs (JavaScript/TypeScript, Java) sont inchangés (FR-009).
- Les golden files existants ne DOIVENT pas bouger (python-demo n'est pas en layout
  `src/`) ; un nouveau golden couvre le corpus `src-layout-demo`.
