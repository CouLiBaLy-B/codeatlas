"""Comparaison de deux Baselines → ArchDelta (FR-002/FR-003).

Comparaison ensembliste sur identifiants stables ; une API présente des deux côtés
avec une signature différente est rapportée « modifiée » (jamais apparu+disparu).
Pas de détection de renommage (assumé par la spec).
"""

from __future__ import annotations

from dataclasses import dataclass

from codeatlas.baseline.capture import Baseline

# catégories dont une APPARITION est une régression potentielle (rendu en tête)
REGRESSION_ON_APPEARED = ("package_cycles", "layer_violations", "inferred_calls", "dead_code")
# catégories dont une DISPARITION est une régression potentielle
REGRESSION_ON_DISAPPEARED = ("public_api",)


@dataclass(frozen=True, slots=True)
class CategoryDelta:
    appeared: tuple[str, ...]
    disappeared: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModifiedApi:
    id: str
    old_signature: str
    new_signature: str


@dataclass(frozen=True, slots=True)
class MetricDelta:
    name: str
    old: int
    new: int


@dataclass(frozen=True, slots=True)
class ArchDelta:
    """Delta architectural — uniquement les catégories qui changent, triées."""

    categories: tuple[tuple[str, CategoryDelta], ...]
    modified_api: tuple[ModifiedApi, ...]
    metric_deltas: tuple[MetricDelta, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.categories or self.modified_api or self.metric_deltas)

    def category(self, name: str) -> CategoryDelta | None:
        return dict(self.categories).get(name)


def _pair_text(pair: tuple[str, str]) -> str:
    return f"{pair[0]} → {pair[1]}"


def _displays(baseline: Baseline) -> dict[str, dict[str, str]]:
    """Par catégorie : clé stable → texte d'affichage traçable."""
    return {
        "package_cycles": {
            "|".join(cycle): " → ".join(cycle) for cycle in baseline.package_cycles
        },
        "layer_violations": {
            "|".join(pair): _pair_text(pair) for pair in baseline.layer_violations
        },
        "inferred_calls": {
            "|".join(pair): _pair_text(pair) for pair in baseline.inferred_calls
        },
        "dead_code": {
            identifier: f"{identifier} ({confidence})"
            for identifier, confidence in baseline.dead_code
        },
        "service_deps": {
            "|".join(pair): _pair_text(pair) for pair in baseline.service_deps
        },
        "subprojects": {
            sub_id: f"{sub_id} ({language})" for sub_id, language in baseline.subprojects
        },
        "skipped": {path: f"{path} — {reason}" for path, reason in baseline.skipped},
    }


def compare(old: Baseline, new: Baseline) -> ArchDelta:
    """Delta déterministe entre deux baselines compatibles."""
    categories: list[tuple[str, CategoryDelta]] = []

    # API publique : existence par id, signature = identité (modifiée si changée)
    old_api = {entry.id: entry for entry in old.public_api}
    new_api = {entry.id: entry for entry in new.public_api}
    appeared_api = tuple(
        f"{new_api[i].id} {new_api[i].signature}".strip()
        for i in sorted(set(new_api) - set(old_api))
    )
    disappeared_api = tuple(
        f"{old_api[i].id} {old_api[i].signature}".strip()
        for i in sorted(set(old_api) - set(new_api))
    )
    modified = tuple(
        ModifiedApi(
            id=identifier,
            old_signature=old_api[identifier].signature,
            new_signature=new_api[identifier].signature,
        )
        for identifier in sorted(set(old_api) & set(new_api))
        if old_api[identifier].signature != new_api[identifier].signature
    )
    if appeared_api or disappeared_api:
        categories.append(
            ("public_api", CategoryDelta(appeared=appeared_api, disappeared=disappeared_api))
        )

    old_displays = _displays(old)
    new_displays = _displays(new)
    for name in sorted(old_displays):
        old_entries, new_entries = old_displays[name], new_displays[name]
        appeared = tuple(new_entries[k] for k in sorted(set(new_entries) - set(old_entries)))
        disappeared = tuple(
            old_entries[k] for k in sorted(set(old_entries) - set(new_entries))
        )
        if appeared or disappeared:
            categories.append((name, CategoryDelta(appeared=appeared, disappeared=disappeared)))

    old_metrics, new_metrics = dict(old.metrics), dict(new.metrics)
    metric_deltas = tuple(
        MetricDelta(name=name, old=old_metrics.get(name, 0), new=new_metrics.get(name, 0))
        for name in sorted(set(old_metrics) | set(new_metrics))
        if old_metrics.get(name, 0) != new_metrics.get(name, 0)
    )

    return ArchDelta(
        categories=tuple(sorted(categories)),
        modified_api=modified,
        metric_deltas=metric_deltas,
    )
