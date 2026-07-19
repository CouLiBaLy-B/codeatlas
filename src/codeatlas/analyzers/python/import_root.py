"""Détection de la racine d'import Python (feature 005).

Le nom qualifié d'un module doit être celui qu'un `import` désigne, pas son chemin
sur le disque. Sur un layout `src/` (ou un package rangé dans un sous-répertoire), la
racine analysée n'est pas la racine d'import : ce module la déduit statiquement, par la
seule structure des packages (présence d'`__init__.py`), sans rien exécuter ni
consulter de `sys.path` réel (constitution I).

Contrat : specs/005-source-root-detection/contracts/source-root.md.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath

_INIT = "__init__.py"


def _dirname(posix_path: str) -> str:
    """Répertoire contenant `posix_path` ; racine du dépôt → chaîne vide."""
    parent = PurePosixPath(posix_path).parent.as_posix()
    return "" if parent == "." else parent


def detect_import_roots(paths: Sequence[str]) -> dict[str, str]:
    """Associe à chaque chemin `.py` sa racine d'import (préfixe à retirer du nom).

    Pour un fichier, on remonte tant que le répertoire courant est un package (contient
    `__init__.py`) ; le premier ancêtre qui n'est PAS un package est la racine d'import.
    Un package déjà à la racine analysée donne une racine vide (comportement historique,
    aucune régression). Pur et déterministe : ne dépend que de l'ensemble des chemins.
    """
    package_dirs = {_dirname(p) for p in paths if PurePosixPath(p).name == _INIT}
    roots: dict[str, str] = {}
    for path in sorted(paths):
        directory = _dirname(path)
        while directory != "" and directory in package_dirs:
            directory = _dirname(directory)
        roots[path] = directory
    return roots
