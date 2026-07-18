"""Lecture/écriture des baselines : JSON canonique, archives, contrôle de version.

Une baseline incompatible produit une erreur d'usage explicite — jamais une
comparaison silencieusement fausse (FR-006).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from codeatlas.baseline.capture import BASELINE_VERSION, ApiEntry, Baseline
from codeatlas.ir.model import IR_VERSION

_LABEL = re.compile(r"^[A-Za-z0-9._-]+$")


class BaselineError(Exception):
    """Baseline illisible ou incompatible (erreur d'usage, exit 2 côté CLI)."""


def default_path(root: Path) -> Path:
    return root / ".codeatlas" / "baseline.json"


def history_dir(root: Path) -> Path:
    return root / ".codeatlas" / "history"


def to_json(baseline: Baseline) -> str:
    """JSON canonique : clés triées, listes triées, UTF-8, fin `\\n`."""
    payload = {
        "baseline_version": baseline.baseline_version,
        "ir_version": baseline.ir_version,
        "root": baseline.root,
        "subprojects": [
            {"id": sub_id, "language": language} for sub_id, language in baseline.subprojects
        ],
        "public_api": [
            {"id": e.id, "kind": e.kind, "signature": e.signature} for e in baseline.public_api
        ],
        "package_cycles": [list(cycle) for cycle in baseline.package_cycles],
        "layer_violations": [
            {"source": source, "target": target}
            for source, target in baseline.layer_violations
        ],
        "inferred_calls": [
            {"source": source, "target": target} for source, target in baseline.inferred_calls
        ],
        "dead_code": [
            {"id": identifier, "confidence": confidence}
            for identifier, confidence in baseline.dead_code
        ],
        "service_deps": [
            {"source": source, "target": target} for source, target in baseline.service_deps
        ],
        "skipped": [{"path": path, "reason": reason} for path, reason in baseline.skipped],
        "metrics": dict(baseline.metrics),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def from_json(text: str) -> Baseline:
    """Relit une baseline en validant format et compatibilité de versions."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BaselineError(f"baseline illisible (JSON invalide) : {exc}") from exc
    try:
        baseline_version = payload["baseline_version"]
        ir_version = payload["ir_version"]
        if baseline_version != BASELINE_VERSION or ir_version != IR_VERSION:
            raise BaselineError(
                "baseline incompatible (format "
                f"{baseline_version}/IR {ir_version}, attendu {BASELINE_VERSION}/"
                f"{IR_VERSION}) — veuillez la recapturer avec `codeatlas baseline`"
            )
        return Baseline(
            baseline_version=baseline_version,
            ir_version=ir_version,
            root=payload["root"],
            subprojects=tuple(
                (entry["id"], entry["language"]) for entry in payload["subprojects"]
            ),
            public_api=tuple(
                ApiEntry(id=e["id"], kind=e["kind"], signature=e["signature"])
                for e in payload["public_api"]
            ),
            package_cycles=tuple(tuple(cycle) for cycle in payload["package_cycles"]),
            layer_violations=tuple(
                (entry["source"], entry["target"]) for entry in payload["layer_violations"]
            ),
            inferred_calls=tuple(
                (entry["source"], entry["target"]) for entry in payload["inferred_calls"]
            ),
            dead_code=tuple(
                (entry["id"], entry["confidence"]) for entry in payload["dead_code"]
            ),
            service_deps=tuple(
                (entry["source"], entry["target"]) for entry in payload["service_deps"]
            ),
            skipped=tuple((entry["path"], entry["reason"]) for entry in payload["skipped"]),
            metrics=tuple(sorted(payload["metrics"].items())),
        )
    except (KeyError, TypeError) as exc:
        raise BaselineError(f"baseline illisible (champ manquant : {exc}) — recapturer") from exc


def write(baseline: Baseline, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(to_json(baseline))


def load(path: Path) -> Baseline:
    if not path.is_file():
        raise BaselineError(
            f"baseline introuvable : {path} — lancez `codeatlas baseline` pour la créer"
        )
    return from_json(path.read_text(encoding="utf-8"))


def archive(baseline: Baseline, root: Path, label: str) -> Path:
    if not _LABEL.match(label):
        raise BaselineError(f"label d'archive invalide : {label!r} (attendu [A-Za-z0-9._-]+)")
    target = history_dir(root) / f"{label}.json"
    write(baseline, target)
    return target


def natural_key(label: str) -> tuple[object, ...]:
    """Tri naturel documenté : les segments numériques comparés numériquement
    (v10 > v2)."""
    return tuple(
        int(part) if part.isdigit() else part for part in re.split(r"(\d+)", label)
    )


def list_archives(root: Path) -> list[tuple[str, Baseline]]:
    """Baselines archivées, triées par label en ordre naturel croissant."""
    directory = history_dir(root)
    if not directory.is_dir():
        return []
    entries = []
    for path in directory.glob("*.json"):
        entries.append((path.stem, load(path)))
    return sorted(entries, key=lambda item: natural_key(item[0]))
