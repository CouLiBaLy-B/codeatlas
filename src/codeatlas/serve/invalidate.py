"""Analyse incrémentale par unités de sous-projet (US3, FR-010).

Les fragments d'IR sont indépendants entre sous-projets (aucune arête de nœuds ne
traverse les sous-projets ; les liens inter-services sont recalculés à
l'assemblage) : re-analyser les seules unités touchées puis réassembler produit
EXACTEMENT le même graphe qu'une analyse complète — invariant testé.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from codeatlas.analyzers.base import available_analyzers
from codeatlas.api import (
    AnalysisUnit,
    CodeAtlasError,
    _analyze_unit,
    _assemble_graph,
    _discover_units,
)
from codeatlas.config import Config
from codeatlas.ir.model import CodeGraph
from codeatlas.monorepo.detect import MANIFEST_LANGUAGES

_STRUCTURAL_FILES = frozenset({name for name, _ in MANIFEST_LANGUAGES} | {"codeatlas.toml"})


class IncrementalAnalyzer:
    """Ré-analyse le dépôt en réutilisant les fragments des unités intactes."""

    def __init__(self, root: Path, config: Config) -> None:
        self.root = root.resolve()
        self.config = config
        self._subs: list[Any] = []
        self._units: list[AnalysisUnit] = []
        self._fragments: dict[str, Any] = {}
        self._graph: CodeGraph | None = None

    # -- classification --------------------------------------------------------

    def is_structural(self, path: str) -> bool:
        """Un manifeste change la carte des sous-projets → tout est réanalysé."""
        return PurePosixPath(path).name in _STRUCTURAL_FILES

    def _code_extensions(self) -> set[str]:
        return {ext for a in available_analyzers().values() for ext in a.extensions}

    def affected_subprojects(self, changed: set[str]) -> list[str]:
        """Sous-projets propriétaires des chemins modifiés (racine la plus profonde)."""
        affected: set[str] = set()
        monorepo = len(self._subs) > 1
        for path in changed:
            suffix = PurePosixPath(path).suffix
            for unit in self._units:
                extensions = available_analyzers()[unit.language].extensions
                if suffix not in extensions:
                    continue
                if not monorepo:
                    affected.add(unit.subproject.id)
                    continue
                root = unit.subproject.root
                if root in (".", "") or path == root or path.startswith(f"{root}/"):
                    affected.add(unit.subproject.id)
        if monorepo:
            # seule la racine correspondante la plus profonde possède le fichier
            deepest: set[str] = set()
            roots = {u.subproject.id: u.subproject.root for u in self._units}
            for path in changed:
                best_id, best_len = None, -1
                for sub_id in affected:
                    root = roots[sub_id]
                    depth = 0 if root in (".", "") else len(root)
                    owns = root in (".", "") or path == root or path.startswith(f"{root}/")
                    if owns and depth > best_len:
                        best_id, best_len = sub_id, depth
                if best_id is not None:
                    deepest.add(best_id)
            affected = deepest
        return sorted(affected)

    # -- analyse ----------------------------------------------------------------

    def _fail_if_empty(self, analyzed_any: bool) -> None:
        if not analyzed_any:
            raise CodeAtlasError(f"aucun fichier analysable trouvé dans {self.root}")

    def _full(self) -> CodeGraph:
        subs, units = _discover_units(self.root, self.config)
        fragments = {unit.subproject.id: _analyze_unit(unit, self.config) for unit in units}
        graph, analyzed_any = _assemble_graph(
            self.root.name, subs, [(u, fragments[u.subproject.id]) for u in units]
        )
        self._fail_if_empty(analyzed_any)
        self._subs, self._units, self._fragments, self._graph = subs, units, fragments, graph
        return graph

    def analyze(self, changed: set[str] | None = None) -> CodeGraph:
        """Graphe à jour ; `changed` = chemins POSIX relatifs au dépôt, ou None."""
        if self._graph is None or changed is None:
            return self._full()
        if any(self.is_structural(path) for path in changed):
            return self._full()
        code_extensions = self._code_extensions()
        code_changed = {
            p for p in changed if PurePosixPath(p).suffix in code_extensions
        }
        if not code_changed:
            return self._graph  # rien d'analysable n'a bougé
        affected = set(self.affected_subprojects(code_changed))
        if not affected:
            return self._full()  # nouveau langage / zone inconnue : on repart à zéro

        subs, units = _discover_units(self.root, self.config)
        if {u.subproject.id for u in units} != {u.subproject.id for u in self._units}:
            self._subs, self._units = subs, units
            return self._full()  # une unité est apparue ou a disparu
        fragments = {}
        for unit in units:
            sub_id = unit.subproject.id
            if sub_id in affected or sub_id not in self._fragments:
                fragments[sub_id] = _analyze_unit(unit, self.config)
            else:
                fragments[sub_id] = self._fragments[sub_id]
        graph, analyzed_any = _assemble_graph(
            self.root.name, subs, [(u, fragments[u.subproject.id]) for u in units]
        )
        self._fail_if_empty(analyzed_any)
        self._subs, self._units, self._fragments, self._graph = subs, units, fragments, graph
        return graph
