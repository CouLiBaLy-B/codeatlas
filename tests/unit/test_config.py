"""T010 — Tests de la configuration : fusion, validation stricte, suggestions."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeatlas.config import DEFAULT_EXCLUDES, Config, ConfigError, load_config


class TestDefaults:
    def test_defaults_without_any_file(self, tmp_path: Path) -> None:
        config = load_config(tmp_path)
        assert config.project.language == "en"
        assert config.analysis.include_private is False
        assert config.graphs.call_depth == 3
        assert config.metrics.complexity_warn == 10
        assert config.metrics.complexity_critical == 20
        assert config.site.enabled is True
        assert config.check.min_doc_coverage == -1

    def test_default_excludes_cover_common_directories(self) -> None:
        joined = " ".join(DEFAULT_EXCLUDES)
        for fragment in ("node_modules", ".venv", "__pycache__", "dist", "build", "target"):
            assert fragment in joined


class TestResolution:
    def test_codeatlas_toml_overrides_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "codeatlas.toml").write_text(
            '[project]\ntitle = "Demo"\nlanguage = "fr"\n\n[graphs]\ncall_depth = 5\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert config.project.title == "Demo"
        assert config.project.language == "fr"
        assert config.graphs.call_depth == 5
        assert config.metrics.complexity_warn == 10  # défaut préservé

    def test_pyproject_tool_section_used_as_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[tool.codeatlas.project]\ntitle = "ViaPyproject"\n', encoding="utf-8"
        )
        assert load_config(tmp_path).project.title == "ViaPyproject"

    def test_codeatlas_toml_wins_over_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[tool.codeatlas.project]\ntitle = "Perdant"\n', encoding="utf-8"
        )
        (tmp_path / "codeatlas.toml").write_text('[project]\ntitle = "Gagnant"\n', encoding="utf-8")
        assert load_config(tmp_path).project.title == "Gagnant"

    def test_explicit_file_has_highest_priority(self, tmp_path: Path) -> None:
        (tmp_path / "codeatlas.toml").write_text('[project]\ntitle = "Local"\n', encoding="utf-8")
        explicit = tmp_path / "autre.toml"
        explicit.write_text('[project]\ntitle = "Explicite"\n', encoding="utf-8")
        assert load_config(tmp_path, explicit=explicit).project.title == "Explicite"

    def test_missing_explicit_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="introuvable"):
            load_config(tmp_path, explicit=tmp_path / "absent.toml")


class TestValidation:
    def test_unknown_key_rejected_with_suggestion(self, tmp_path: Path) -> None:
        (tmp_path / "codeatlas.toml").write_text('[project]\nlangage = "fr"\n', encoding="utf-8")
        with pytest.raises(ConfigError, match="language"):
            load_config(tmp_path)

    def test_unknown_section_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "codeatlas.toml").write_text("[projet]\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="projet"):
            load_config(tmp_path)

    def test_out_of_domain_depth_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "codeatlas.toml").write_text("[graphs]\ncall_depth = 0\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="call_depth"):
            load_config(tmp_path)

    def test_unsupported_language_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "codeatlas.toml").write_text('[project]\nlanguage = "de"\n', encoding="utf-8")
        with pytest.raises(ConfigError, match="language"):
            load_config(tmp_path)

    def test_bad_type_rejected(self, tmp_path: Path) -> None:
        content = '[graphs]\ncall_depth = "trois"\n'
        (tmp_path / "codeatlas.toml").write_text(content, encoding="utf-8")
        with pytest.raises(ConfigError, match="call_depth"):
            load_config(tmp_path)


class TestUserExcludes:
    def test_user_excludes_are_added_to_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "codeatlas.toml").write_text(
            '[analysis]\nexclude = ["generated/**"]\n', encoding="utf-8"
        )
        config = load_config(tmp_path)
        assert "generated/**" in config.analysis.exclude
        assert set(DEFAULT_EXCLUDES).issubset(set(config.analysis.exclude))


def test_config_is_immutable() -> None:
    config = Config()
    with pytest.raises(AttributeError):
        config.project = None  # type: ignore[misc, assignment]
