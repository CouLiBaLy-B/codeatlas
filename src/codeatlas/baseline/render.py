"""Rendus de l'ArchDelta : texte console, markdown de PR, JSON canonique."""

from __future__ import annotations

import json

from codeatlas.baseline.compare import (
    REGRESSION_ON_APPEARED,
    REGRESSION_ON_DISAPPEARED,
    ArchDelta,
)

PR_MARKER = "<!-- codeatlas:arch-diff -->"
MAX_CONTENT_LINES = 150

_LABELS = {
    "public_api": "API publiques",
    "package_cycles": "Cycles de packages",
    "layer_violations": "Violations de couches",
    "inferred_calls": "Liens d'appel incertains",
    "dead_code": "Code probablement mort",
    "service_deps": "Dépendances inter-services",
    "subprojects": "Sous-projets",
    "skipped": "Fichiers non analysés",
}

EMPTY_MESSAGE = "✅ Aucun changement architectural"


def _ordered_categories(delta: ArchDelta) -> list[tuple[str, bool]]:
    """(nom, est_régression) — régressions potentielles d'abord, ordre stable."""
    names = [name for name, _ in delta.categories]

    def is_regression(name: str) -> bool:
        category = delta.category(name)
        assert category is not None
        return (name in REGRESSION_ON_APPEARED and bool(category.appeared)) or (
            name in REGRESSION_ON_DISAPPEARED and bool(category.disappeared)
        )

    flagged = [(name, is_regression(name)) for name in names]
    return sorted(flagged, key=lambda item: (not item[1], item[0]))


def _lines(delta: ArchDelta, markdown: bool) -> list[str]:
    bullet = "- " if markdown else "  • "
    lines: list[str] = []
    for name, regression in _ordered_categories(delta):
        category = delta.category(name)
        assert category is not None
        icon = "🔴 " if regression else ""
        heading = f"{icon}{_LABELS[name]}"
        lines.append(f"### {heading}" if markdown else heading)
        if category.appeared:
            lines.append(f"{'**' if markdown else ''}Apparus ({len(category.appeared)})"
                         f"{'**' if markdown else ' :'}")
            lines.extend(f"{bullet}`{entry}`" if markdown else f"{bullet}{entry}"
                         for entry in category.appeared)
        if category.disappeared:
            lines.append(f"{'**' if markdown else ''}Disparus ({len(category.disappeared)})"
                         f"{'**' if markdown else ' :'}")
            lines.extend(f"{bullet}`{entry}`" if markdown else f"{bullet}{entry}"
                         for entry in category.disappeared)
        lines.append("")
    if delta.modified_api:
        lines.append("### ⚠️ API modifiées" if markdown else "⚠️ API modifiées")
        for entry in delta.modified_api:
            text = f"{entry.id} : `{entry.old_signature}` → `{entry.new_signature}`"
            lines.append(f"{bullet}{text}" if markdown else f"{bullet}{text.replace('`', '')}")
        lines.append("")
    if delta.metric_deltas:
        lines.append("### Métriques" if markdown else "Métriques")
        for metric in delta.metric_deltas:
            sign = metric.new - metric.old
            lines.append(
                f"{bullet}{metric.name} : {metric.old} → {metric.new} ({sign:+d})"
            )
        lines.append("")
    return lines


def _truncate(lines: list[str]) -> list[str]:
    if len(lines) <= MAX_CONTENT_LINES:
        return lines
    kept = lines[:MAX_CONTENT_LINES]
    omitted = len(lines) - MAX_CONTENT_LINES
    kept.append(f"… tronqué : {omitted} ligne(s) omise(s) — voir `codeatlas diff` en local.")
    return kept


def render_text(delta: ArchDelta) -> str:
    if delta.is_empty:
        return EMPTY_MESSAGE + "\n"
    changed = sum(
        len(c.appeared) + len(c.disappeared) for _, c in delta.categories
    ) + len(delta.modified_api)
    header = [f"Diff architectural — {changed} changement(s)", ""]
    return "\n".join(header + _truncate(_lines(delta, markdown=False))).rstrip("\n") + "\n"


def render_markdown(delta: ArchDelta) -> str:
    """Markdown « commentaire de PR » : marqueur stable, régressions en tête."""
    header = [PR_MARKER, "## Diff architectural CodeAtlas", ""]
    if delta.is_empty:
        return "\n".join([*header, EMPTY_MESSAGE]).rstrip("\n") + "\n"
    changed = sum(
        len(c.appeared) + len(c.disappeared) for _, c in delta.categories
    ) + len(delta.modified_api)
    header.append(f"**{changed} changement(s)** par rapport à la baseline.")
    header.append("")
    return "\n".join(header + _truncate(_lines(delta, markdown=True))).rstrip("\n") + "\n"


def render_json(delta: ArchDelta) -> str:
    payload = {
        "is_empty": delta.is_empty,
        "categories": {
            name: {"appeared": list(c.appeared), "disappeared": list(c.disappeared)}
            for name, c in delta.categories
        },
        "modified_api": [
            {"id": m.id, "old_signature": m.old_signature, "new_signature": m.new_signature}
            for m in delta.modified_api
        ],
        "metrics": [
            {"name": m.name, "old": m.old, "new": m.new} for m in delta.metric_deltas
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
