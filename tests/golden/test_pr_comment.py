"""T016 — Golden tests du markdown « commentaire de PR » (contrat cli.md 002)."""

from __future__ import annotations

from codeatlas.baseline.capture import ApiEntry
from codeatlas.baseline.compare import compare
from codeatlas.baseline.render import MAX_CONTENT_LINES, PR_MARKER, render_markdown
from tests.unit.test_arch_delta import make_baseline


def sample_delta():
    old = make_baseline()
    new = make_baseline(
        public_api=(
            ApiEntry(id="main/pkg.mod.C", kind="class", signature=""),
            ApiEntry(id="main/pkg.mod.g", kind="function", signature="() -> None"),
        ),
        package_cycles=(("pkg.a", "pkg.b"),),
        metrics=(("doc_coverage", 72), ("files_analyzed", 3)),
    )
    return compare(old, new)


def test_pr_comment_matches_golden(assert_golden) -> None:
    assert_golden("pr_comment.md", render_markdown(sample_delta()))


class TestStructure:
    def test_marker_is_first_line(self) -> None:
        assert render_markdown(sample_delta()).splitlines()[0] == PR_MARKER

    def test_regressions_come_first(self) -> None:
        rendered = render_markdown(sample_delta())
        # cycle (régression 🔴) avant l'API apparue (neutre)
        assert rendered.index("Cycles de packages") < rendered.index("pkg.mod.g")
        assert "🔴" in rendered

    def test_empty_delta_is_explicit(self) -> None:
        rendered = render_markdown(compare(make_baseline(), make_baseline()))
        assert rendered.splitlines()[0] == PR_MARKER
        assert "Aucun changement architectural" in rendered

    def test_modified_api_paired(self) -> None:
        new = make_baseline(
            public_api=(
                ApiEntry(id="main/pkg.mod.f", kind="function", signature="(x: str) -> int"),
                ApiEntry(id="main/pkg.mod.C", kind="class", signature=""),
            )
        )
        rendered = render_markdown(compare(make_baseline(), new))
        assert "API modifiées" in rendered
        assert "`(x: int) -> int` → `(x: str) -> int`" in rendered


class TestTruncation:
    def test_huge_delta_truncated_with_exact_count(self) -> None:
        many = tuple(
            ApiEntry(id=f"main/pkg.mod.f{i:04d}", kind="function", signature="()")
            for i in range(400)
        )
        delta = compare(make_baseline(public_api=()), make_baseline(public_api=many))
        rendered = render_markdown(delta)
        lines = rendered.splitlines()
        assert "tronqué" in rendered
        assert "omise(s)" in rendered
        # le contenu (hors en-tête) est borné
        assert len(lines) < MAX_CONTENT_LINES + 12
