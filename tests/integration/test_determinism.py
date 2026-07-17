"""T022 — SC-002 : deux exécutions → sorties identiques octet pour octet."""

from __future__ import annotations

import filecmp
from pathlib import Path

from click.testing import CliRunner

from codeatlas.cli import main


def _tree_bytes(root: Path) -> dict[str, bytes]:
    files = (p for p in sorted(root.rglob("*")) if p.is_file())
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in files}


def test_double_run_is_byte_identical(tmp_path: Path, corpus: Path, runner: CliRunner) -> None:
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    for out in (out_a, out_b):
        result = runner.invoke(main, ["build", str(corpus), "--out", str(out)])
        assert result.exit_code == 0, result.output

    tree_a, tree_b = _tree_bytes(out_a), _tree_bytes(out_b)
    assert tree_a.keys() == tree_b.keys()
    different = [name for name, blob in tree_a.items() if tree_b[name] != blob]
    assert different == [], f"fichiers non déterministes : {different}"


def test_rebuild_into_same_directory_is_stable(
    tmp_path: Path, corpus: Path, runner: CliRunner
) -> None:
    out = tmp_path / "same"
    reference = tmp_path / "ref"
    for target in (out, reference):
        assert runner.invoke(main, ["build", str(corpus), "--out", str(target)]).exit_code == 0
    # seconde exécution PAR-DESSUS une sortie existante
    assert runner.invoke(main, ["build", str(corpus), "--out", str(out)]).exit_code == 0
    comparison = filecmp.dircmp(out, reference)
    assert not comparison.diff_files
    assert not comparison.left_only and not comparison.right_only


def test_no_absolute_paths_leak_into_artifacts(
    tmp_path: Path, corpus: Path, runner: CliRunner
) -> None:
    out = tmp_path / "leak"
    assert runner.invoke(main, ["build", str(corpus), "--out", str(out)]).exit_code == 0
    offenders = []
    for page in (out / "docs").rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        if str(corpus) in text or str(tmp_path) in text:
            offenders.append(page.name)
    assert offenders == []
