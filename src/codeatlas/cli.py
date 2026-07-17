"""CLI de CodeAtlas — façade fine au-dessus de `codeatlas.api`.

Contrat : specs/001-intelligent-doc-generator/contracts/cli.md.
Exit codes : 0 succès (avertissements possibles), 1 erreur fatale,
2 erreur d'usage, 3 seuil `check` violé.
Messages humains → stderr ; données machine (JSON, diagrammes) → stdout.
"""

from __future__ import annotations

import json
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
        json_report.parent.mkdir(parents=True, exist_ok=True)
        json_report.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not quiet:
        render_console(report, _stderr, verbose=verbose)
        _stderr.print(f"[green]Documentation générée dans[/green] {out}")
    sys.exit(EXIT_OK)


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
def check(path: Path) -> None:
    """Mode CI : évalue les seuils qualité (livré avec la user story 4)."""
    _stderr.print("[red]erreur :[/red] `codeatlas check` sera livré avec la user story 4")
    sys.exit(EXIT_FATAL)


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
def diagram(path: Path) -> None:
    """Diagramme focalisé (livré avec la user story 2)."""
    _stderr.print("[red]erreur :[/red] `codeatlas diagram` sera livré avec la user story 2")
    sys.exit(EXIT_FATAL)


if __name__ == "__main__":  # pragma: no cover
    main()
