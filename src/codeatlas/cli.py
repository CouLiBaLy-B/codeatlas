"""CLI de CodeAtlas — façade fine au-dessus de `codeatlas.api`.

Contrat : specs/001-intelligent-doc-generator/contracts/cli.md.
Exit codes : 0 succès (avertissements possibles), 1 erreur fatale,
2 erreur d'usage, 3 seuil `check` violé.
Messages humains → stderr ; données machine (JSON, diagrammes) → stdout.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from rich.console import Console

from codeatlas import __version__, api
from codeatlas.config import Config, ConfigError, load_config
from codeatlas.report.render import render_console

EXIT_OK = 0
EXIT_FATAL = 1
EXIT_USAGE = 2
EXIT_CHECK_FAILED = 3

_stderr = Console(stderr=True)


def _load_config_or_exit(path: Path, config_file: Path | None) -> Config:
    try:
        return load_config(path.resolve(), explicit=config_file)
    except ConfigError as exc:
        _stderr.print(f"[red]erreur de configuration :[/red] {exc}")
        sys.exit(EXIT_USAGE)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="codeatlas")
def main() -> None:
    """CodeAtlas : documentation générée par analyse statique — hors-ligne, sans LLM."""


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", "-o", type=click.Path(path_type=Path), default=Path("codeatlas-docs"))
@click.option("--config", "-c", "config_file", type=click.Path(path_type=Path), default=None)
@click.option("--exclude", multiple=True, help="Motif glob d'exclusion (répétable).")
@click.option("--include-private", is_flag=True, help="Inclut les symboles privés.")
@click.option("--depth", type=int, default=None, help="Profondeur des graphes d'appels.")
@click.option("--site/--no-site", "with_site", default=True)
@click.option("--svg", is_flag=True, help="Exporte aussi les diagrammes en SVG.")
@click.option("--json-report", type=click.Path(path_type=Path), default=None)
@click.option("--quiet", is_flag=True)
@click.option("--verbose", is_flag=True)
def build(
    path: Path,
    out: Path,
    config_file: Path | None,
    exclude: tuple[str, ...],
    include_private: bool,
    depth: int | None,
    with_site: bool,
    svg: bool,
    json_report: Path | None,
    quiet: bool,
    verbose: bool,
) -> None:
    """Génère la documentation complète du dépôt PATH."""
    from dataclasses import replace

    config = _load_config_or_exit(path, config_file)
    if exclude:
        config = replace(
            config,
            analysis=replace(config.analysis, exclude=(*config.analysis.exclude, *exclude)),
        )
    if include_private:
        config = replace(config, analysis=replace(config.analysis, include_private=True))
    if depth is not None:
        if depth < 1:
            _stderr.print("[red]erreur d'usage :[/red] --depth doit être ≥ 1")
            sys.exit(EXIT_USAGE)
        config = replace(config, graphs=replace(config.graphs, call_depth=depth))
    config = replace(
        config,
        site=replace(config.site, enabled=with_site, svg_export=svg or config.site.svg_export),
    )

    started = time.monotonic()
    try:
        graph = api.analyze(path, config)
        report = api.build_site(graph, out, config)
    except api.CodeAtlasError as exc:
        _stderr.print(f"[red]erreur :[/red] {exc}")
        sys.exit(EXIT_FATAL)
    report.duration_seconds = round(time.monotonic() - started, 3)

    if json_report is not None:
        from codeatlas.report.json import report_to_json

        json_report.parent.mkdir(parents=True, exist_ok=True)
        json_report.write_text(report_to_json(report), encoding="utf-8", newline="\n")
    if not quiet:
        render_console(report, _stderr, verbose=verbose)
        for warning in report.warnings:
            if warning.code == "svg-unavailable":
                _stderr.print(f"[yellow]note SVG :[/yellow] {warning.detail}")
        _stderr.print(f"[green]Documentation générée dans[/green] {out}")
    sys.exit(EXIT_OK)


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--config", "-c", "config_file", type=click.Path(path_type=Path), default=None)
@click.option("--max-package-cycles", type=int, default=None)
@click.option("--min-doc-coverage", type=int, default=None)
@click.option("--max-critical-symbols", type=int, default=None)
@click.option("--json-report", type=click.Path(path_type=Path), default=None)
def check(
    path: Path,
    config_file: Path | None,
    max_package_cycles: int | None,
    min_doc_coverage: int | None,
    max_critical_symbols: int | None,
    json_report: Path | None,
) -> None:
    """Mode CI : évalue les seuils qualité, exit 3 si au moins un est violé."""
    from dataclasses import replace

    from codeatlas.report.json import report_to_json
    from codeatlas.report.model import AnalysisReport

    config = _load_config_or_exit(path, config_file)
    thresholds = config.check
    if max_package_cycles is not None:
        thresholds = replace(thresholds, max_package_cycles=max_package_cycles)
    if min_doc_coverage is not None:
        thresholds = replace(thresholds, min_doc_coverage=min_doc_coverage)
    if max_critical_symbols is not None:
        thresholds = replace(thresholds, max_critical_symbols=max_critical_symbols)

    started = time.monotonic()
    try:
        graph = api.analyze(path, config)
        results = api.run_checks(graph, thresholds, config)
    except api.CodeAtlasError as exc:
        _stderr.print(f"[red]erreur :[/red] {exc}")
        sys.exit(EXIT_FATAL)

    report = AnalysisReport(root=graph.root)
    report.files_analyzed = sum(1 for n in graph.iter_nodes() if n.kind.value == "module")
    report.files_skipped = len(graph.skipped)
    report.nodes = len(graph.nodes)
    report.edges_certain = sum(1 for e in graph.edges if e.certainty.value == "certain")
    report.edges_inferred = sum(1 for e in graph.edges if e.certainty.value == "inferred")
    report.skipped = [{"path": s.path, "reason": s.reason} for s in graph.skipped]
    report.checks = results
    report.duration_seconds = round(time.monotonic() - started, 3)

    if json_report is not None:
        json_report.parent.mkdir(parents=True, exist_ok=True)
        json_report.write_text(report_to_json(report), encoding="utf-8", newline="\n")

    render_console(report, _stderr)
    failed = [c for c in results if not c.passed]
    if failed:
        _stderr.print(f"[red]{len(failed)} seuil(s) violé(s)[/red]")
        for result in failed:
            click.echo(
                f"FAIL {result.name}: {result.actual} (seuil {result.threshold})"
            )
        sys.exit(EXIT_CHECK_FAILED)
    sys.exit(EXIT_OK)


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--type",
    "-t",
    "diagram_type",
    type=click.Choice(["class", "deps", "calls"]),
    default="class",
)
@click.option("--focus", default=None, help="Nom qualifié ou nom court non ambigu.")
@click.option("--depth", type=int, default=None, help="Rayon autour du symbole focal.")
@click.option("--out", type=click.Path(path_type=Path), default=None, help="Fichier .mmd.")
@click.option("--config", "-c", "config_file", type=click.Path(path_type=Path), default=None)
def diagram(
    path: Path,
    diagram_type: str,
    focus: str | None,
    depth: int | None,
    out: Path | None,
    config_file: Path | None,
) -> None:
    """Émet un diagramme focalisé sur stdout (ou dans --out)."""
    config = _load_config_or_exit(path, config_file)
    try:
        graph = api.analyze(path, config)
        rendered = api.render_diagram(
            graph,
            api.DiagramSpec(type=diagram_type, focus=focus, depth=depth),
            config,
        )
    except api.FocusError as exc:
        _stderr.print(f"[red]erreur d'usage :[/red] {exc}")
        sys.exit(EXIT_USAGE)
    except api.CodeAtlasError as exc:
        _stderr.print(f"[red]erreur :[/red] {exc}")
        sys.exit(EXIT_FATAL)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        click.echo(rendered, nl=False)
    sys.exit(EXIT_OK)


if __name__ == "__main__":  # pragma: no cover
    main()
