
"""
ArchGuard AI — Directed Dependency Edge Renderer.

Draws dependency arrows in a Plotly graph.

Features:
    - Curved arrows for reciprocal dependencies
    - Straight arrows for one-way dependencies
    - Directional arrowheads
    - Dependency hover descriptions
    - Deterministic geometry
    - No changes to the underlying dependency graph
"""

from __future__ import annotations

import math

import plotly.graph_objects as go


def _point_on_curve(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    """Return a point on a quadratic Bezier curve."""

    u = 1.0 - t

    x = (
        u * u * start[0]
        + 2.0 * u * t * control[0]
        + t * t * end[0]
    )

    y = (
        u * u * start[1]
        + 2.0 * u * t * control[1]
        + t * t * end[1]
    )

    return x, y


def add_curved_dependency_edges(
    fig: go.Figure,
    positions: dict,
    dependencies: list[dict],
    *,
    color: str = "#64748b",
    curvature: float = 0.22,
) -> go.Figure:
    """
    Add directed dependency edges to an existing Plotly figure.

    Parameters
    ----------
    fig:
        Existing Plotly figure.

    positions:
        Mapping of module names to (x, y) coordinates.

    dependencies:
        List of dictionaries with 'source' and 'target'.

    color:
        Arrow and line color.

    curvature:
        Curve strength for bidirectional relationships.

    Returns
    -------
    go.Figure:
        The same figure with directed edges added.
    """

    edge_pairs = {
        (dep["source"], dep["target"])
        for dep in dependencies
        if (
            isinstance(dep, dict)
            and "source" in dep
            and "target" in dep
        )
    }

    # Sort for reproducible trace ordering.
    for source, target in sorted(edge_pairs):

        if source not in positions or target not in positions:
            continue

        if source == target:
            # Self-dependencies need a dedicated loop renderer.
            continue

        start = tuple(positions[source])
        end = tuple(positions[target])

        dx = end[0] - start[0]
        dy = end[1] - start[1]

        distance = math.hypot(dx, dy)

        if distance == 0:
            continue

        # Perpendicular unit vector.
        nx = -dy / distance
        ny = dx / distance

        reciprocal = (target, source) in edge_pairs

        # For reciprocal edges, each traversal bends to
        # its own left side, giving separate visible paths.
        bend = curvature * distance if reciprocal else 0.0

        midpoint_x = (start[0] + end[0]) / 2.0
        midpoint_y = (start[1] + end[1]) / 2.0

        control = (
            midpoint_x + nx * bend,
            midpoint_y + ny * bend,
        )

        # Trim the curve so the arrow does not terminate
        # at the exact center of its target node.
        trim = min(0.12, 0.08 / distance)

        start_t = trim
        end_t = 1.0 - trim

        samples = 32

        points = [
            _point_on_curve(
                start,
                control,
                end,
                start_t
                + (end_t - start_t) * i / (samples - 1),
            )
            for i in range(samples)
        ]

        xs = [point[0] for point in points]
        ys = [point[1] for point in points]

        description = f"{source} imports {target}"

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={
                    "color": color,
                    "width": 2,
                },
                text=[description] * len(xs),
                hovertemplate="%{text}<extra></extra>",
                name=description,
                showlegend=False,
            )
        )

        # Draw an arrowhead aligned with the tangent
        # near the end of the Bezier curve.
        arrow_start = points[-3]
        arrow_end = points[-1]

        fig.add_annotation(
            x=arrow_end[0],
            y=arrow_end[1],
            ax=arrow_start[0],
            ay=arrow_start[1],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.2,
            arrowwidth=2,
            arrowcolor=color,
            opacity=0.95,
            text="",
        )

    return fig
