"""Configuration optionnelle de CodeAtlas (codeatlas.toml / [tool.codeatlas]).

Contrat : specs/001-intelligent-doc-generator/contracts/config-schema.md.
Résolution : fichier explicite > codeatlas.toml > pyproject [tool.codeatlas] > défauts.
Toute clé inconnue ou valeur hors domaine est une erreur (jamais d'ignorance
silencieuse).
"""

from __future__ import annotations

import difflib
import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

SUPPORTED_SITE_LANGUAGES = ("en", "fr")

DEFAULT_EXCLUDES: tuple[str, ...] = (
    "**/node_modules/**",
    "**/.venv/**",
    "**/venv/**",
    "**/__pycache__/**",
    "**/dist/**",
    "**/build/**",
    "**/target/**",
    "**/.git/**",
    "**/.codeatlas/**",  # baselines du diff architectural — jamais analysées
    "**/vendor/**",
    "**/.*/**",
    "**/*.min.js",
)


class ConfigError(Exception):
    """Configuration invalide : clé inconnue, type ou valeur hors domaine."""


@dataclass(frozen=True, slots=True)
class ProjectCfg:
    title: str = ""
    language: str = "en"


@dataclass(frozen=True, slots=True)
class AnalysisCfg:
    include_private: bool = False
    exclude: tuple[str, ...] = DEFAULT_EXCLUDES
    languages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphsCfg:
    call_depth: int = 3
    focus_depth: int = 1


@dataclass(frozen=True, slots=True)
class MetricsCfg:
    complexity_warn: int = 10
    complexity_critical: int = 20
    doc_coverage_warn: int = 60


@dataclass(frozen=True, slots=True)
class SiteCfg:
    enabled: bool = True
    out: str = "codeatlas-docs"
    extra_nav: tuple[str, ...] = ()
    svg_export: bool = False


@dataclass(frozen=True, slots=True)
class CheckCfg:
    max_package_cycles: int = -1
    min_doc_coverage: int = -1
    max_critical_symbols: int = -1
    # règles de régression contre la baseline (feature 002) — opt-in
    fail_on_new_cycles: bool = False
    fail_on_new_violations: bool = False
    fail_on_new_inferred: bool = False
    fail_on_removed_public_api: bool = False
    max_doc_coverage_drop: int = -1  # points de % ; -1 = désactivé


@dataclass(frozen=True, slots=True)
class ExportCfg:
    budget: int = 24000  # caractères de la carte repomap (≥ 2000)


@dataclass(frozen=True, slots=True)
class MonorepoCfg:
    detect: bool = True
    roots: tuple[str, ...] = ()


EXPLORER_METRICS = ("loc", "complexity", "doc_coverage", "fan_in", "fan_out")


@dataclass(frozen=True, slots=True)
class ExplorerCfg:
    enabled: bool = True
    include_source: bool = True
    default_metric: str = "complexity"  # métrique initiale de la treemap


@dataclass(frozen=True, slots=True)
class Config:
    project: ProjectCfg = field(default_factory=ProjectCfg)
    analysis: AnalysisCfg = field(default_factory=AnalysisCfg)
    graphs: GraphsCfg = field(default_factory=GraphsCfg)
    metrics: MetricsCfg = field(default_factory=MetricsCfg)
    site: SiteCfg = field(default_factory=SiteCfg)
    check: CheckCfg = field(default_factory=CheckCfg)
    export: ExportCfg = field(default_factory=ExportCfg)
    monorepo: MonorepoCfg = field(default_factory=MonorepoCfg)
    explorer: ExplorerCfg = field(default_factory=ExplorerCfg)


def _suggest(unknown: str, candidates: list[str]) -> str:
    matches = difflib.get_close_matches(unknown, candidates, n=1)
    return f" — vouliez-vous dire {matches[0]!r} ?" if matches else ""


def _coerce(section: str, key: str, current: Any, value: Any) -> Any:
    """Vérifie le type d'une valeur TOML et la convertit vers le type du défaut."""
    if isinstance(current, bool):
        if not isinstance(value, bool):
            raise ConfigError(f"[{section}].{key} : booléen attendu, reçu {value!r}")
        return value
    if isinstance(current, int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigError(f"[{section}].{key} : entier attendu, reçu {value!r}")
        return value
    if isinstance(current, str):
        if not isinstance(value, str):
            raise ConfigError(f"[{section}].{key} : chaîne attendue, reçu {value!r}")
        return value
    if isinstance(current, tuple):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(f"[{section}].{key} : liste de chaînes attendue, reçu {value!r}")
        return tuple(value)
    raise ConfigError(f"[{section}].{key} : type non supporté")  # pragma: no cover


def _apply_section(config: Config, section_name: str, values: dict[str, Any]) -> Config:
    section = getattr(config, section_name)
    known_keys = [f.name for f in fields(section)]
    for key, value in values.items():
        if key not in known_keys:
            raise ConfigError(
                f"clé inconnue [{section_name}].{key}{_suggest(key, known_keys)}"
            )
        current = getattr(section, key)
        section = replace(section, **{key: _coerce(section_name, key, current, value)})
    return replace(config, **{section_name: section})


def _apply(config: Config, data: dict[str, Any]) -> Config:
    section_names = [f.name for f in fields(config)]
    for section_name, values in data.items():
        if section_name not in section_names:
            raise ConfigError(
                f"section inconnue [{section_name}]{_suggest(section_name, section_names)}"
            )
        if not isinstance(values, dict):
            raise ConfigError(f"[{section_name}] doit être une table TOML")
        config = _apply_section(config, section_name, values)
    return config


def _validate(config: Config) -> None:
    if config.project.language not in SUPPORTED_SITE_LANGUAGES:
        raise ConfigError(
            f"[project].language : {config.project.language!r} non supporté "
            f"(choix : {', '.join(SUPPORTED_SITE_LANGUAGES)})"
        )
    if config.graphs.call_depth < 1:
        raise ConfigError("[graphs].call_depth : doit être ≥ 1")
    if config.graphs.focus_depth < 1:
        raise ConfigError("[graphs].focus_depth : doit être ≥ 1")
    if not 0 <= config.metrics.doc_coverage_warn <= 100:
        raise ConfigError("[metrics].doc_coverage_warn : pourcentage attendu (0-100)")
    if config.check.min_doc_coverage != -1 and not 0 <= config.check.min_doc_coverage <= 100:
        raise ConfigError("[check].min_doc_coverage : pourcentage attendu (0-100) ou -1")
    drop = config.check.max_doc_coverage_drop
    if drop != -1 and not 0 <= drop <= 100:
        raise ConfigError("[check].max_doc_coverage_drop : points attendus (0-100) ou -1")
    if config.export.budget < 2000:
        raise ConfigError("[export].budget : minimum 2000 caractères")
    if config.explorer.default_metric not in EXPLORER_METRICS:
        raise ConfigError(
            f"[explorer].default_metric : {config.explorer.default_metric!r} inconnu "
            f"(choix : {', '.join(EXPLORER_METRICS)})"
        )


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path.name} : TOML invalide — {exc}") from exc


def load_config(root: Path, explicit: Path | None = None) -> Config:
    """Charge la configuration effective pour un dépôt analysé."""
    data: dict[str, Any] | None = None
    if explicit is not None:
        if not explicit.is_file():
            raise ConfigError(f"fichier de configuration introuvable : {explicit}")
        data = _read_toml(explicit)
    elif (root / "codeatlas.toml").is_file():
        data = _read_toml(root / "codeatlas.toml")
    elif (root / "pyproject.toml").is_file():
        pyproject = _read_toml(root / "pyproject.toml")
        tool = pyproject.get("tool", {})
        if isinstance(tool, dict) and "codeatlas" in tool:
            data = tool["codeatlas"]

    config = Config()
    if data is not None:
        # Les exclusions utilisateur s'AJOUTENT aux défauts (FR-006).
        user_excludes = data.get("analysis", {}).get("exclude")
        config = _apply(config, data)
        if user_excludes is not None:
            merged = tuple(dict.fromkeys((*DEFAULT_EXCLUDES, *config.analysis.exclude)))
            config = replace(config, analysis=replace(config.analysis, exclude=merged))
    _validate(config)
    return config
