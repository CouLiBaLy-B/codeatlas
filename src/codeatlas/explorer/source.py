"""Extraits de source des fiches (US5) — découpés depuis les emplacements de l'IR.

Lecture tolérante (encodage remplacé, fichier illisible → None, jamais d'échec) ;
le rendu (coloration, repli) appartient au site, ce module ne fait que découper.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from codeatlas.ir.model import Node

MAX_LINES = 120  # borne d'affichage : une fiche n'est pas un pager


@dataclass(frozen=True, slots=True)
class SourceExcerpt:
    path: str
    start_line: int
    end_line: int
    code: str
    truncated: bool = False


def extract_excerpt(source_root: Path, node: Node) -> SourceExcerpt | None:
    """Extrait exact de la définition (`location` + `loc` de l'IR) ; None si illisible."""
    target = source_root / node.location.file
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    start = node.location.line
    if start < 1 or start > len(lines):
        return None
    span = max(node.loc, 1)
    end = min(start + span - 1, len(lines))
    truncated = end - start + 1 > MAX_LINES
    if truncated:
        end = start + MAX_LINES - 1
    code = "\n".join(lines[start - 1 : end])
    return SourceExcerpt(
        path=node.location.file,
        start_line=start,
        end_line=end,
        code=code,
        truncated=truncated,
    )
