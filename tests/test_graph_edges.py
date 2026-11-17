
"""
Tests for ArchGuard AI's directed edge renderer.

Run:
    python -m pytest tests/test_graph_edges.py -v
"""

import plotly.graph_objects as go

from archguard.dashboard.graph_edges import (
    add_curved_dependency_edges,
)


def test_one_way_dependency():
    fig = go.Figure()

    result = add_curved_dependency_edges(
        fig,
        {"a": (0, 0), "b": (1, 0)},
        [{"source": "a", "target": "b"}],
    )

    assert result is fig
    assert len(fig.data) == 1
    assert len(fig.layout.annotations) == 1
    assert fig.data[0].name == "a imports b"


def test_bidirectional_dependencies_are_separate():
    fig = go.Figure()

    add_curved_dependency_edges(
        fig,
        {"a": (0, 0), "b": (1, 0)},
        [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "a"},
        ],
    )

    assert len(fig.data) == 2
    assert len(fig.layout.annotations) == 2

    # Verify the two directed edges bend onto
    # opposite sides of the straight center line.
    first_y = list(fig.data[0].y)
    second_y = list(fig.data[1].y)

    assert max(first_y) > 0
    assert min(second_y) < 0


def test_missing_positions_are_ignored():
    fig = go.Figure()

    add_curved_dependency_edges(
        fig,
        {"a": (0, 0)},
        [{"source": "a", "target": "b"}],
    )

    assert len(fig.data) == 0


def test_duplicate_dependencies_render_once():
    fig = go.Figure()

    add_curved_dependency_edges(
        fig,
        {"a": (0, 0), "b": (1, 0)},
        [
            {"source": "a", "target": "b"},
            {"source": "a", "target": "b"},
        ],
    )

    assert len(fig.data) == 1


def test_self_dependency_is_skipped():
    fig = go.Figure()

    add_curved_dependency_edges(
        fig,
        {"a": (0, 0)},
        [{"source": "a", "target": "a"}],
    )

    assert len(fig.data) == 0


def test_edge_order_is_deterministic():
    positions = {
        "a": (0, 0),
        "b": (1, 0),
        "c": (2, 0),
    }

    edges = [
        {"source": "c", "target": "b"},
        {"source": "a", "target": "b"},
    ]

    first = go.Figure()
    second = go.Figure()

    add_curved_dependency_edges(
        first, positions, edges
    )

    add_curved_dependency_edges(
        second, positions, list(reversed(edges))
    )

    assert [
        trace.name for trace in first.data
    ] == [
        trace.name for trace in second.data
    ]
