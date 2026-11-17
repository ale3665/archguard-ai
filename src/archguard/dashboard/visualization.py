
"""
ArchGuard AI — Layer-Aware Architecture Visualization.

Builds an interactive directed dependency graph using
NetworkX and Plotly.

This module does not depend on Streamlit or FastAPI.
"""

import networkx as nx
import plotly.graph_objects as go


LAYER_COLORS = {
    "Domain": "#16A34A",
    "Application": "#D97706",
    "Adapters": "#2563EB",
    "Dashboard": "#9333EA",
    "Bootstrap": "#DC2626",
    "Other": "#64748B",
}

LAYER_ORDER = tuple(LAYER_COLORS)


def classify_module(module_name: str) -> str:
    """Identify the architectural layer of a Python module."""

    parts = module_name.split(".")

    # ArchGuard's package structure.
    if parts[0] == "archguard" and len(parts) > 1:
        layer = parts[1]

        mapping = {
            "domain": "Domain",
            "application": "Application",
            "adapters": "Adapters",
            "dashboard": "Dashboard",
            "bootstrap": "Bootstrap",
        }

        return mapping.get(layer, "Other")

    return "Other"


def create_dependency_figure(
    modules: list[dict],
    dependencies: list[dict],
    visible_layers: list[str] | None = None,
) -> go.Figure:
    """
    Build a layer-aware directed dependency graph.

    Nodes are grouped by architectural layer.
    Edges represent real dependencies provided by the API.

    Args:
        modules: Module dictionaries returned by the API.
        dependencies: Internal dependency dictionaries.
        visible_layers: Optional layer selection.

    Returns:
        Interactive Plotly figure.
    """

    if visible_layers is None:
        visible = set(LAYER_ORDER)
    else:
        visible = set(visible_layers)

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
            graph.add_edge(source, target)

    figure = go.Figure()

    # Handle empty project or empty filter selection.
    if graph.number_of_nodes() == 0:
        figure.update_layout(
            title="No modules match the selected layers",
            height=450,
            showlegend=False,
        )
        return figure

    # Group modules by architecture layer.
    groups = {
        layer: sorted(
            node
            for node in graph.nodes()
            if graph.nodes[node]["layer"] == layer
        )
        for layer in LAYER_ORDER
    }

    active_layers = [
        layer for layer in LAYER_ORDER
        if groups[layer]
    ]

    # Use deterministic positions rather than a
    # force-directed layout.
    # Each layer receives its own vertical column.
    positions = {}

    max_group_size = max(
        len(groups[layer])
        for layer in active_layers
    )

    for column, layer in enumerate(active_layers):
        names = groups[layer]

        for index, name in enumerate(names):
            x = float(column)
            y = (len(names) - 1) / 2 - index

            positions[name] = (x, y)

    # --------------------------------------------------------
    # Draw real directed dependencies
    # --------------------------------------------------------

    for source, target in sorted(graph.edges()):
        x0, y0 = positions[source]
        x1, y1 = positions[target]

        # Arrow annotations show dependency direction.
        figure.add_annotation(
            x=x1,
            y=y1,
            ax=x0,
            ay=y0,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor="#94A3B8",
            opacity=0.55,
        )

    # --------------------------------------------------------
    # Draw modules by architectural layer
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

            short_name = name.split(".")[-1]
            node_labels.append(short_name)

            incoming = graph.in_degree(name)
            outgoing = graph.out_degree(name)

            hover_labels.append(
                f"<b>{name}</b>"
                f"<br>Layer: {layer}"
                f"<br>Incoming: {incoming}"
                f"<br>Outgoing: {outgoing}"
            )

            node_sizes.append(
                min(36, 18 + graph.degree(name) * 2)
            )

        figure.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                name=layer,
                text=node_labels,
                textposition="top center",
                textfont=dict(size=10),
                customdata=hover_labels,
                hovertemplate="%{customdata}<extra></extra>",
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
    # Layout and navigation
    # --------------------------------------------------------

    figure.update_layout(
        title="Architecture Dependency Graph",
        height=max(650, max_group_size * 105),
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
        ),
        yaxis=dict(
            visible=False,
            range=[
                -max_group_size / 2 - 0.5,
                max_group_size / 2 + 0.5,
            ],
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )

    return figure
