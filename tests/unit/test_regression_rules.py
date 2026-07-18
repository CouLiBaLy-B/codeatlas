"""T012 — Règles de régression du gate : opt-in, passe/échoue par catégorie."""

from __future__ import annotations

from codeatlas.baseline.capture import ApiEntry
from codeatlas.baseline.compare import compare
from codeatlas.config import CheckCfg
from codeatlas.insights.checks import evaluate_regressions

from .test_arch_delta import make_baseline


def results_for(delta, **rules):
    return {r.name: r.passed for r in evaluate_regressions(delta, CheckCfg(**rules))}


class TestOptIn:
    def test_no_rule_enabled_no_result(self) -> None:
        delta = compare(make_baseline(), make_baseline(package_cycles=(("a", "b"),)))
        assert evaluate_regressions(delta, CheckCfg()) == []


class TestRules:
    def test_new_cycle_fails_rule(self) -> None:
        delta = compare(make_baseline(), make_baseline(package_cycles=(("a", "b"),)))
        assert results_for(delta, fail_on_new_cycles=True) == {"fail-on-new-cycles": False}

    def test_no_new_cycle_passes_rule(self) -> None:
        old = make_baseline(package_cycles=(("a", "b"),))
        delta = compare(old, old)
        assert results_for(delta, fail_on_new_cycles=True) == {"fail-on-new-cycles": True}

    def test_preexisting_cycle_does_not_fail(self) -> None:
        # un cycle déjà présent dans la baseline n'est pas une RÉGRESSION
        old = make_baseline(package_cycles=(("a", "b"),))
        new = make_baseline(package_cycles=(("a", "b"),), metrics=(("doc_coverage", 79),))
        assert results_for(compare(old, new), fail_on_new_cycles=True) == {
            "fail-on-new-cycles": True
        }

    def test_new_violation_and_inferred(self) -> None:
        delta = compare(
            make_baseline(),
            make_baseline(
                layer_violations=(("infra", "api"),),
                inferred_calls=(("a", "b"),),
            ),
        )
        outcome = results_for(delta, fail_on_new_violations=True, fail_on_new_inferred=True)
        assert outcome == {"fail-on-new-violations": False, "fail-on-new-inferred": False}

    def test_removed_public_api_fails_rule(self) -> None:
        old = make_baseline()
        new = make_baseline(
            public_api=(ApiEntry(id="main/pkg.mod.C", kind="class", signature=""),)
        )
        assert results_for(compare(old, new), fail_on_removed_public_api=True) == {
            "fail-on-removed-public-api": False
        }

    def test_doc_coverage_drop_threshold(self) -> None:
        old = make_baseline()  # doc_coverage 80
        new = make_baseline(metrics=(("doc_coverage", 70), ("files_analyzed", 3)))
        delta = compare(old, new)
        assert results_for(delta, max_doc_coverage_drop=5) == {"max-doc-coverage-drop": False}
        assert results_for(delta, max_doc_coverage_drop=15) == {"max-doc-coverage-drop": True}

    def test_coverage_rise_never_fails(self) -> None:
        old = make_baseline(metrics=(("doc_coverage", 70), ("files_analyzed", 3)))
        new = make_baseline()  # 80
        assert results_for(compare(old, new), max_doc_coverage_drop=0) == {
            "max-doc-coverage-drop": True
        }
