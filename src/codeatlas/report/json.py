"""Export JSON canonique de l'AnalysisReport (schéma stable, contrat cli.md)."""

from __future__ import annotations

import json

from codeatlas.report.model import AnalysisReport


def report_to_json(report: AnalysisReport) -> str:
    """JSON stable : clés triées, UTF-8, fin de ligne unique."""
    return (
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
