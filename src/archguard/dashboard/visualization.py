
"""
ArchGuard AI — Layer-Aware Architecture Visualization.

Builds an interactive, directed dependency graph using
NetworkX and Plotly.

Features:
    - Architectural layer classification
    - Consistent colors for architectural layers
    - Deterministic node positioning
    - Interactive module hover information
    - Directional dependency arrows
    - Curved arrows for bidirectional dependencies
    - Layer-based graph filtering
    - Dynamic visualization height
    - Graceful handling of empty graphs

This module does not depend on Streamlit or FastAPI.

Dependencies:
    networkx
    plotly

Internal dependency:
    archguard.dashboard.graph_edges
"""

import networkx as nx
import plotly.graph_objects as go

from archguard.dashboard.graph_edges import (
    add_curved_dependency_edges,
)


# ============================================================
# Architectural Layer Configuration
# ============================================================

LAYER_COLORS = {
    "Domain": "#16A34A",
    "Application": "#D97706",
    "Adapters": "#2563EB",
    "Dashboard": "#9333EA",
    "Bootstrap": "#DC2626",
    "Other": "#64748B",
}

LAYER_ORDER = tuple(LAYER_COLORS)


# ============================================================
# Module Layer Classification
# ============================================================

def classify_module(module_name: str) -> str:
    """
    Identify the architectural layer of a Python module.

    ArchGuard's package structure:

        archguard.domain.*
        archguard.application.*
        archguard.adapters.*
        archguard.dashboard.*
        archguard.bootstrap

    All other modules are assigned to the Other layer.
    """

    parts = module_name.split(".")

    if parts[0] == "archguard" and len(parts) > 1:

        layer = parts[1]

        mapping = {
            "domain": "Domain",
            "application": "Application",
            "adapters": "Adapters",
            "dashboard": "Dashboard",
            "bootstrap": "Bootstrap",
        }

        return mapping.get(
            layer,
            "Other",
        )

    return "Other"


# ============================================================
# Architecture Dependency Graph
# ============================================================

def create_dependency_figure(
    modules: list[dict],
    dependencies: list[dict],
    visible_layers: list[str] | None = None,
) -> go.Figure:
    """
    Build an interactive layer-aware dependency graph.

    Parameters
    ----------
    modules:
        Module dictionaries returned by the ArchGuard API.

    dependencies:
        Verified internal dependency relationships.

        Expected format:
            {
                "source": "module_a",
                "target": "module_b"
            }

    visible_layers:
        Optional architectural layer selection.

        When None, all layers are displayed.

    Returns
    -------
    plotly.graph_objects.Figure:
        Interactive architecture dependency visualization.

    Notes
    -----
    Dependency relationships originate from ArchGuard's
    deterministic static analysis engine.

    The graph renderer does not infer or generate
    additional architectural dependencies.
    """

    # --------------------------------------------------------
    # Determine visible architecture layers
    # --------------------------------------------------------

    if visible_layers is None:
        visible = set(LAYER_ORDER)
    else:
        visible = set(visible_layers)

    # --------------------------------------------------------
    # Create directed NetworkX graph
    # --------------------------------------------------------

    graph = nx.DiGraph()

    # Register modules belonging to selected layers.
    for module in modules:

        name = module["name"]
        layer = classify_module(name)

        if layer in visible:

            graph.add_node(
                name,
                layer=layer,
            )

    # Register dependencies only when both endpoints
    # belong to the visible graph.
    for dependency in dependencies:

        source = dependency["source"]
        target = dependency["target"]

        if source in graph and target in graph:

            graph.add_edge(
                source,
                target,
            )

    # --------------------------------------------------------
    # Initialize Plotly figure
    # --------------------------------------------------------

    figure = go.Figure()

    # --------------------------------------------------------
    # Handle empty graph or empty filter selection
    # --------------------------------------------------------

    if graph.number_of_nodes() == 0:

        figure.update_layout(
            title="No modules match the selected layers",
            height=450,
            showlegend=False,
        )

        return figure

    # --------------------------------------------------------
    # Group modules by architectural layer
    # --------------------------------------------------------

    groups = {
        layer: sorted(
            node
            for node in graph.nodes()
            if graph.nodes[node]["layer"] == layer
        )
        for layer in LAYER_ORDER
    }

    active_layers = [
        layer
        for layer in LAYER_ORDER
        if groups[layer]
    ]

    # --------------------------------------------------------
    # Calculate deterministic node positions
    # --------------------------------------------------------

    # Each architectural layer receives its own
    # vertical column.
    #
    # Within each column, module positions are
    # determined alphabetically.
    #
    # This ensures the same architecture produces
    # the same layout across repeated analyses.

    positions = {}

    max_group_size = max(
        len(groups[layer])
        for layer in active_layers
    )

    for column, layer in enumerate(active_layers):

        names = groups[layer]

        for index, name in enumerate(names):

            x = float(column)

            y = (
                (len(names) - 1) / 2
                - index
            )

            positions[name] = (
                x,
                y,
            )

    # --------------------------------------------------------
    # Step 21: Draw curved directional dependencies
    # --------------------------------------------------------

    # Convert actual NetworkX edges to the format
    # accepted by the tested edge renderer.
    #
    # IMPORTANT:
    # The edge renderer is responsible only for
    # displaying existing dependencies.
    #
    # It does not detect new dependency relationships.

    visible_dependencies = [
        {
            "source": source,
            "target": target,
        }
        for source, target in sorted(
            graph.edges()
        )
    ]

    # Render dependencies before nodes so that
    # module markers remain visually prominent.
    #
    # Reciprocal dependencies:
    #     a -> b
    #     b -> a
    #
    # are displayed as separate curved arrows.
    #
    # One-way dependencies remain straight.

    add_curved_dependency_edges(
        fig=figure,
        positions=positions,
        dependencies=visible_dependencies,
        color="#94A3B8",
        curvature=0.22,
    )

    # --------------------------------------------------------
    # Draw modules grouped by architecture layer
    # --------------------------------------------------------

    for layer in active_layers:

        names = groups[layer]

        node_x = []
        node_y = []

        node_labels = []
        hover_labels = []
        node_sizes = []

        for name in names:

            x, y = positions[name]

            node_x.append(x)
            node_y.append(y)

            # Display only the final module component.
            # Full module names remain available on hover.
            short_name = name.split(".")[-1]

            node_labels.append(
                short_name
            )

            # NetworkX in-degree and out-degree provide
            # verified dependency counts.
            incoming = graph.in_degree(name)
            outgoing = graph.out_degree(name)

            hover_labels.append(
                f"<b>{name}</b>"
                f"<br>Layer: {layer}"
                f"<br>Incoming: {incoming}"
                f"<br>Outgoing: {outgoing}"
            )

            # Increase marker size slightly for modules
            # with more dependency relationships.
            node_sizes.append(
                min(
                    36,
                    18 + graph.degree(name) * 2,
                )
            )

        # ----------------------------------------------------
        # Plotly module trace
        # ----------------------------------------------------

        figure.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,

                mode="markers+text",

                name=layer,

                text=node_labels,

                textposition="top center",

                textfont=dict(
                    size=10,
                ),

                customdata=hover_labels,

                hovertemplate=(
                    "%{customdata}<extra></extra>"
                ),

                marker=dict(
                    size=node_sizes,
                    color=LAYER_COLORS[layer],
                    opacity=0.9,
                    line=dict(
                        color="#FFFFFF",
                        width=1.5,
                    ),
                ),
            )
        )

    # --------------------------------------------------------
    # Configure Plotly layout
    # --------------------------------------------------------

    figure.update_layout(
        title="Architecture Dependency Graph",

        height=max(
            650,
            max_group_size * 105,
        ),

        showlegend=True,

        legend=dict(
            title="Architecture Layers",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),

        hovermode="closest",

        dragmode="pan",

        margin=dict(
            l=80,
            r=80,
            t=115,
            b=60,
        ),

        xaxis=dict(
            visible=False,
            range=[
                -0.5,
                len(active_layers) - 0.5,
            ],
            showgrid=False,
            zeroline=False,
        ),

        yaxis=dict(
            visible=False,
            range=[
                -max_group_size / 2 - 0.5,
                max_group_size / 2 + 0.5,
            ],
            showgrid=False,
            zeroline=False,
        ),

        plot_bgcolor="#FFFFFF",

        paper_bgcolor="#FFFFFF",
    )

    return figure
