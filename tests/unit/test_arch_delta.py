"""T007 — Moteur de comparaison : apparu/disparu, API modifiées, déterminisme."""

from __future__ import annotations

from typing import Any

from codeatlas.baseline.capture import BASELINE_VERSION, ApiEntry, Baseline
from codeatlas.baseline.compare import ArchDelta, compare


def make_baseline(**overrides: Any) -> Baseline:
    defaults: dict[str, Any] = {
        "baseline_version": BASELINE_VERSION,
        "ir_version": 1,
        "root": "demo",
        "subprojects": (("main", "python"),),
        "public_api": (
            ApiEntry(id="main/pkg.mod.f", kind="function", signature="(x: int) -> int"),
            ApiEntry(id="main/pkg.mod.C", kind="class", signature=""),
        ),
        "package_cycles": (),
        "layer_violations": (),
        "inferred_calls": (),
        "dead_code": (),
        "service_deps": (),
        "skipped": (),
        "metrics": (("doc_coverage", 80), ("files_analyzed", 3)),
    }
    defaults.update(overrides)
    return Baseline(**defaults)


def category(delta: ArchDelta, name: str):
    return dict(delta.categories).get(name)


class TestEmptyDelta:
    def test_identical_baselines_produce_empty_delta(self) -> None:
        delta = compare(make_baseline(), make_baseline())
        assert delta.is_empty
        assert delta.categories == ()
        assert delta.modified_api == ()
        assert delta.metric_deltas == ()


class TestCategories:
    def test_new_cycle_appears(self) -> None:
        new = make_baseline(package_cycles=(("pkg.a", "pkg.b"),))
        delta = compare(make_baseline(), new)
        cycles = category(delta, "package_cycles")
        assert cycles is not None
        assert cycles.appeared == ("pkg.a → pkg.b",)
        assert cycles.disappeared == ()
        assert not delta.is_empty

    def test_removed_public_api_disappears(self) -> None:
        old = make_baseline()
        new = make_baseline(
            public_api=(ApiEntry(id="main/pkg.mod.C", kind="class", signature=""),)
        )
        delta = compare(old, new)
        api = category(delta, "public_api")
        assert api is not None
        assert api.disappeared == ("main/pkg.mod.f (x: int) -> int",)
        assert api.appeared == ()

    def test_new_violation_and_inferred_call(self) -> None:
        new = make_baseline(
            layer_violations=(("pkg.infra", "pkg.api"),),
            inferred_calls=(("main/pkg.mod.f", "main/pkg.mod.C.g"),),
        )
        delta = compare(make_baseline(), new)
        assert category(delta, "layer_violations").appeared == ("pkg.infra → pkg.api",)
        assert category(delta, "inferred_calls").appeared == (
            "main/pkg.mod.f → main/pkg.mod.C.g",
        )


class TestModifiedApi:
    def test_signature_change_is_paired_not_added_removed(self) -> None:
        new = make_baseline(
            public_api=(
                ApiEntry(id="main/pkg.mod.f", kind="function", signature="(x: str) -> int"),
                ApiEntry(id="main/pkg.mod.C", kind="class", signature=""),
            )
        )
        delta = compare(make_baseline(), new)
        assert len(delta.modified_api) == 1
        modified = delta.modified_api[0]
        assert modified.id == "main/pkg.mod.f"
        assert modified.old_signature == "(x: int) -> int"
        assert modified.new_signature == "(x: str) -> int"
        assert category(delta, "public_api") is None  # ni apparu ni disparu


class TestMetrics:
    def test_metric_drop_reported(self) -> None:
        new = make_baseline(metrics=(("doc_coverage", 70), ("files_analyzed", 3)))
        delta = compare(make_baseline(), new)
        deltas = {d.name: (d.old, d.new) for d in delta.metric_deltas}
        assert deltas == {"doc_coverage": (80, 70)}


def test_determinism() -> None:
    old = make_baseline()
    new = make_baseline(package_cycles=(("pkg.a", "pkg.b"),), metrics=(("doc_coverage", 75),))
    assert compare(old, new) == compare(old, new)
