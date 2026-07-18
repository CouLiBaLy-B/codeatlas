"""T012 — Index de recherche de symboles (US2, FR-006/007/008)."""

from __future__ import annotations

from codeatlas.config import AnalysisCfg, Config
from codeatlas.explorer.search import build_search_index
from codeatlas.ir.model import (
    CodeGraph,
    DocFormat,
    DocInfo,
    Location,
    Node,
    NodeKind,
    SubProject,
    Visibility,
)


def _page_for(module_id: str) -> str:
    return f"modules/{module_id.split('/', 1)[-1]}.html"


def _node(node_id: str, kind: NodeKind, **kwargs) -> Node:
    name = node_id.rsplit(".", 1)[-1]
    defaults = {
        "id": node_id,
        "kind": kind,
        "name": name,
        "subproject": "main",
        "location": Location(file="app.py", line=1),
    }
    defaults.update(kwargs)
    return Node(**defaults)


def _graph() -> CodeGraph:
    graph = CodeGraph(root="demo")
    graph.add_subproject(SubProject(id="main", language="python", root="."))
    graph.add_node(_node("main/app.orders", NodeKind.MODULE))
    graph.add_node(_node("main/app.billing", NodeKind.MODULE))
    graph.add_node(
        _node(
            "main/app.orders.Order",
            NodeKind.CLASS,
            doc=DocInfo(raw="Une commande.", summary="Une commande.", format=DocFormat.DOCSTRING),
        )
    )
    graph.add_node(_node("main/app.billing.Order", NodeKind.CLASS))  # homonyme
    graph.add_node(
        _node("main/app.orders.Order.total", NodeKind.METHOD, signature="(self) -> float")
    )
    graph.add_node(
        _node("main/app.orders.checkout", NodeKind.FUNCTION, signature="(cart: Cart) -> Order")
    )
    graph.add_node(
        _node("main/app.orders._helper", NodeKind.FUNCTION, visibility=Visibility.PRIVATE)
    )
    graph.add_node(_node("main/app.orders.Order.tax", NodeKind.ATTRIBUTE))  # jamais indexé
    return graph


def test_one_entry_per_symbol_kind() -> None:
    entries = build_search_index(_graph(), Config(), _page_for)
    kinds = {(e["qualname"], e["kind"]) for e in entries}
    assert ("app.orders", "module") in kinds
    assert ("app.orders.Order", "class") in kinds
    assert ("app.orders.Order.total", "method") in kinds
    assert ("app.orders.checkout", "function") in kinds
    assert all(kind != "attribute" for _, kind in kinds)


def test_homonyms_are_disambiguated_by_qualname() -> None:
    entries = build_search_index(_graph(), Config(), _page_for)
    orders = [e for e in entries if e["name"] == "Order"]
    assert len(orders) == 2
    assert {e["qualname"] for e in orders} == {"app.orders.Order", "app.billing.Order"}
    assert {e["module"] for e in orders} == {"app.orders", "app.billing"}


def test_entries_carry_signature_language_and_valid_page() -> None:
    entries = build_search_index(_graph(), Config(), _page_for)
    checkout = next(e for e in entries if e["qualname"] == "app.orders.checkout")
    assert checkout["signature"] == "(cart: Cart) -> Order"
    assert checkout["language"] == "python"
    assert checkout["page"].startswith("modules/app.orders.html")
    method = next(e for e in entries if e["kind"] == "method")
    assert method["page"] == "modules/app.orders.html#order"  # ancre de sa classe


def test_private_symbols_follow_config() -> None:
    entries = build_search_index(_graph(), Config(), _page_for)
    assert all(e["name"] != "_helper" for e in entries)
    config = Config(analysis=AnalysisCfg(include_private=True))
    entries_private = build_search_index(_graph(), config, _page_for)
    assert any(e["name"] == "_helper" for e in entries_private)


def test_sorted_by_name_then_qualname_and_deterministic() -> None:
    first = build_search_index(_graph(), Config(), _page_for)
    second = build_search_index(_graph(), Config(), _page_for)
    assert first == second
    keys = [(e["name"], e["qualname"]) for e in first]
    assert keys == sorted(keys)
