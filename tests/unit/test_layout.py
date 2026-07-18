"""T006 — Layout hiérarchique déterministe (US1, R2) : rangs, entiers, sans aléa."""

from __future__ import annotations

from codeatlas.explorer.layout import layered_positions


def test_dag_ranks_follow_edge_direction() -> None:
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("b", "c"), ("a", "d")]
    pos = layered_positions(nodes, edges)
    assert pos["a"][0] < pos["b"][0] < pos["c"][0]
    assert pos["a"][0] < pos["d"][0]


def test_cycle_members_share_a_rank_without_crash() -> None:
    pos = layered_positions(["a", "b", "z"], [("a", "b"), ("b", "a"), ("b", "z")])
    assert pos["a"][0] == pos["b"][0]  # cycle → même rang (SCC)
    assert pos["b"][0] < pos["z"][0]


def test_positions_are_integers_and_distinct_within_rank() -> None:
    nodes = [f"n{i}" for i in range(6)]
    pos = layered_positions(nodes, [])  # aucun lien : tous au rang 0
    for x, y in pos.values():
        assert isinstance(x, int) and isinstance(y, int)
    assert len({pos[n] for n in nodes}) == len(nodes)  # jamais deux nœuds superposés


def test_isolated_nodes_are_included() -> None:
    pos = layered_positions(["seul"], [])
    assert pos == {"seul": (0, 0)}


def test_strictly_deterministic_regardless_of_input_order() -> None:
    nodes = ["c", "a", "b", "e", "d"]
    edges = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "e")]
    first = layered_positions(nodes, edges)
    second = layered_positions(list(reversed(nodes)), list(reversed(edges)))
    assert first == second
