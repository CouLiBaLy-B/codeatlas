"""Tableau de bord explorable (US4) : lignes de métriques + treemap squarify.

Le layout de la treemap est calculé ici, au build (algorithme squarify classique,
arrondis aux bords partagés : jamais de chevauchement ni de trou) puis rendu en
SVG cliquable — déterministe et lisible sans JavaScript (FR-014, SC-007).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from codeatlas.config import Config
from codeatlas.explorer.graphview import build_graph_view

_CANVAS_W = 1000
_CANVAS_H = 560
_PALETTE = ("#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452", "#9a60b4")


def _worst_ratio(row: list[float], side: float) -> float:
    total = sum(row)
    if total <= 0 or side <= 0:
        return float("inf")
    worst = 0.0
    for value in row:
        width = total / side
        height = value / width
        worst = max(worst, width / height, height / width)
    return worst


def _layout_row(
    row: list[tuple[str, float]], x: float, y: float, w: float, h: float
) -> tuple[list[tuple[str, float, float, float, float]], float, float, float, float]:
    """Pose une rangée le long du petit côté → rects float + rectangle restant."""
    total = sum(value for _, value in row)
    rects = []
    if w >= h:  # rangée verticale à gauche
        width = total / h
        offset = y
        for identifier, value in row:
            height = value / width
            rects.append((identifier, x, offset, width, height))
            offset += height
        return rects, x + width, y, w - width, h
    height = total / w
    offset = x
    for identifier, value in row:
        width = value / height
        rects.append((identifier, offset, y, width, height))
        offset += width
    return rects, x, y + height, w, h - height


def _squarify(
    items: list[tuple[str, float]], x: float, y: float, w: float, h: float
) -> list[tuple[str, float, float, float, float]]:
    """Squarify (Bruls et al.) — entrée triée par valeur décroissante."""
    rects: list[tuple[str, float, float, float, float]] = []
    row: list[tuple[str, float]] = []
    index = 0
    while index < len(items):
        candidate = [*row, items[index]]
        side = min(w, h)
        if not row or _worst_ratio([v for _, v in candidate], side) <= _worst_ratio(
            [v for _, v in row], side
        ):
            row = candidate
            index += 1
            continue
        placed, x, y, w, h = _layout_row(row, x, y, w, h)
        rects.extend(placed)
        row = []
    if row:
        placed, *_ = _layout_row(row, x, y, w, h)
        rects.extend(placed)
    return rects


def treemap_cells(
    items: list[tuple[str, str, str, float]], width: int = _CANVAS_W, height: int = _CANVAS_H
) -> list[dict[str, Any]]:
    """Cellules entières d'une treemap ; `items` = (id, label, page, valeur > 0)."""
    positive = [(i, label, page, value) for i, label, page, value in items if value > 0]
    if not positive:
        return []
    # tri valeur décroissante puis id : l'ordre du layout est déterministe
    positive.sort(key=lambda item: (-item[3], item[0]))
    total = sum(value for *_, value in positive)
    scale = (width * height) / total
    scaled = [(identifier, value * scale) for identifier, _, _, value in positive]
    placed = _squarify(scaled, 0.0, 0.0, float(width), float(height))
    rects = {identifier: rect for identifier, *rect in placed}
    meta = {identifier: (label, page, value) for identifier, label, page, value in positive}
    cells = []
    for identifier, _, _, _ in positive:
        rx, ry, rw, rh = rects[identifier]
        x0, y0 = round(rx), round(ry)
        x1, y1 = round(rx + rw), round(ry + rh)  # bords partagés → ni trou ni recouvrement
        label, page, value = meta[identifier]
        cells.append(
            {
                "id": identifier,
                "label": label,
                "page": page,
                "x": x0,
                "y": y0,
                "w": max(x1 - x0, 1),
                "h": max(y1 - y0, 1),
                "value": value,
            }
        )
    return cells


def build_dashboard(
    graph: Any, config: Config, page_for: Callable[[str], str]
) -> dict[str, Any]:
    """Lignes par module, avertissements d'analyse et treemap précalculée."""
    view = build_graph_view(graph, config, page_for)
    rows = [
        {
            "id": node["id"],
            "label": node["id"].split("/", 1)[-1],
            "page": node["page"],
            "language": node["language"],
            "layer": node["layer"],
            "subproject": node["subproject"],
            "metrics": node["metrics"],
        }
        for node in view["nodes"]
        if node["level"] == "module"
    ]
    warnings = [
        {"path": s.path, "reason": s.reason, "scope": "file"} for s in graph.skipped
    ]

    metric = config.explorer.default_metric
    used, fallback = metric, ""
    if not any(row["metrics"].get(metric, 0) > 0 for row in rows):
        used, fallback = "loc", "loc"  # métrique vide partout : la taille reste parlante
    items = [
        (row["id"], row["label"], row["page"], float(row["metrics"].get(used, 0)))
        for row in rows
    ]
    cells = treemap_cells(items)
    treemap = {
        "metric": metric,
        "fallback": fallback,
        "cells": cells,
        "omitted": len(rows) - len(cells),
    }
    return {"rows": rows, "warnings": warnings, "treemap": treemap}


def render_treemap_svg(treemap: dict[str, Any], subproject_of: dict[str, str] | None = None) -> str:
    """SVG cliquable autonome (liens natifs : lisible sans JavaScript)."""
    cells = treemap["cells"]
    if not cells:
        return ""
    palette_keys = sorted({(subproject_of or {}).get(c["id"], "") for c in cells})
    lines = [
        f'<svg viewBox="0 0 {_CANVAS_W} {_CANVAS_H}" role="img" '
        'style="max-width:100%;height:auto;font-family:sans-serif">'
    ]
    for cell in cells:
        group = (subproject_of or {}).get(cell["id"], "")
        color = _PALETTE[palette_keys.index(group) % len(_PALETTE)]
        title = f"{cell['label']} — {cell['value']:g}"
        lines.append(f'<a href="{cell["page"]}">')
        lines.append(
            f'<rect x="{cell["x"]}" y="{cell["y"]}" width="{cell["w"]}" height="{cell["h"]}" '
            f'fill="{color}" fill-opacity="0.75" stroke="#ffffff" stroke-width="2">'
            f"<title>{title}</title></rect>"
        )
        if cell["w"] > 7 * len(cell["label"]) + 8 and cell["h"] > 22:
            lines.append(
                f'<text x="{cell["x"] + 6}" y="{cell["y"] + 16}" font-size="12" '
                f'fill="#1a1a1a">{cell["label"]}</text>'
            )
        lines.append("</a>")
    lines.append("</svg>")
    return "".join(lines)
