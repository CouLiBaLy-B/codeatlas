"""T036 — Golden tests des diagrammes de flux d'appels (profondeur, incertains)."""

from __future__ import annotations

from codeatlas.renderers.mermaid.call_flow import render_call_flow

from .corpus import corpus_graph


def test_flow_from_cli_main_depth_3(assert_golden) -> None:
    assert_golden(
        "callflow_main.mmd",
        render_call_flow(corpus_graph(), "main/shopdemo.cli.main", depth=3),
    )


def test_inferred_calls_are_dotted(assert_golden) -> None:
    diagram = render_call_flow(
        corpus_graph(), "main/shopdemo.legacy.pricing.refresh_catalog_price", depth=1
    )
    assert "-.->" in diagram  # lien incertain en pointillés (FR-009)
    assert_golden("callflow_refresh.mmd", diagram)


def test_depth_is_respected() -> None:
    shallow = render_call_flow(corpus_graph(), "main/shopdemo.cli.main", depth=1)
    deep = render_call_flow(corpus_graph(), "main/shopdemo.cli.main", depth=3)
    # à profondeur 1 : place est appelé par main, mais pas ses propres appels
    assert "OrderService.place" in shallow
    assert "InMemoryRepo.find" not in shallow
    assert "InMemoryRepo.find" in deep


def test_callers_included_up_to_depth() -> None:
    diagram = render_call_flow(corpus_graph(), "main/shopdemo.quality.tangled_pricing", depth=1)
    assert "shopdemo.cli.main" in diagram  # appelant à 1 niveau
