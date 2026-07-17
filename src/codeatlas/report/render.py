"""Rendu console (Rich) du rapport d'exécution — messages humains sur stderr."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from codeatlas.report.model import AnalysisReport


def render_console(report: AnalysisReport, console: Console, verbose: bool = False) -> None:
    table = Table(title="CodeAtlas — rapport d'exécution", show_header=False)
    table.add_row("Fichiers analysés", str(report.files_analyzed))
    table.add_row("Fichiers ignorés", str(report.files_skipped))
    table.add_row("Symboles (nœuds)", str(report.nodes))
    table.add_row(
        "Relations (arêtes)",
        f"{report.edges_certain} sûres + {report.edges_inferred} incertaines",
    )
    table.add_row("Durée", f"{report.duration_seconds:.2f}s")
    console.print(table)

    if report.skipped:
        console.print("[yellow]Éléments non analysés :[/yellow]")
        for entry in report.skipped:
            console.print(f"  [yellow]•[/yellow] {entry['path']} — {entry['reason']}")

    if verbose and report.warnings:
        console.print("[yellow]Avertissements :[/yellow]")
        for warning in report.warnings:
            console.print(f"  [yellow]•[/yellow] {warning.code} @ {warning.where} {warning.detail}")

    for check in report.checks:
        status = "[green]OK[/green]" if check.passed else "[red]ÉCHEC[/red]"
        console.print(f"check {check.name} : {check.actual} (seuil {check.threshold}) → {status}")
