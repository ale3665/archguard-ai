
"""
ArchGuard AI — Architecture Visualization Tests.

Tests the layer-aware NetworkX and Plotly visualization.

Coverage:
    1. Architecture layer classification
    2. Architecture layer colors
    3. Dependency graph creation
    4. Architectural layer filtering
    5. Empty graph handling
    6. Empty layer selection
    7. Complete module names in hover information

Step 21 updates:
    - Support separate Plotly traces for dependency edges.
    - Keep architectural layer traces distinguishable.
    - Verify directional dependency arrow annotations.
    - Ensure edge traces do not interfere with module tests.

Run:
    python -m pytest tests/test_visualization.py -v
"""

import plotly.graph_objects as go

from archguard.dashboard.visualization import (
    LAYER_COLORS,
    LAYER_ORDER,
    classify_module,
    create_dependency_figure,
)


# ============================================================
# Shared Test Data
# ============================================================

def sample_modules() -> list[dict]:
    """Return modules belonging to three architecture layers."""

    return [
        {
            "name": "archguard.domain.models",
            "path": "src/archguard/domain/models.py",
        },
        {
            "name": "archguard.application.scanner",
            "path": "src/archguard/application/scanner.py",
        },
        {
            "name": "archguard.adapters.parser",
            "path": "src/archguard/adapters/parser.py",
        },
    ]


def sample_dependencies() -> list[dict]:
    """Return two verified internal module dependencies."""

    return [
        {
            "source": "archguard.application.scanner",
            "target": "archguard.domain.models",
        },
        {
            "source": "archguard.adapters.parser",
            "target": "archguard.domain.models",
        },
    ]


# ============================================================
# Plotly Trace Helpers
# ============================================================

def module_traces(
    figure: go.Figure,
) -> list[go.Scatter]:
    """
    Return only architectural layer traces.

    Module traces have names corresponding to LAYER_COLORS.
    Dependency edge traces use descriptive relationship names.
    """

    return [
        trace
        for trace in figure.data
        if trace.name in LAYER_COLORS
    ]


def dependency_traces(
    figure: go.Figure,
) -> list[go.Scatter]:
    """
    Return only dependency-edge traces.

    These traces represent existing module relationships,
    not architectural layers.
    """

    return [
        trace
        for trace in figure.data
        if trace.name not in LAYER_COLORS
    ]


# ============================================================
# Test 1: Architecture Layer Classification
# ============================================================

def test_classify_architecture_layers():
    """Verify module names map to the correct layers."""

    assert (
        classify_module("archguard.domain.models")
        == "Domain"
    )

    assert (
        classify_module("archguard.application.scanner")
        == "Application"
    )

    assert (
        classify_module("archguard.adapters.ast_parser")
        == "Adapters"
    )

    assert (
        classify_module("archguard.dashboard.app")
        == "Dashboard"
    )

    assert (
        classify_module("archguard.bootstrap")
        == "Bootstrap"
    )

    assert (
        classify_module("external.utility")
        == "Other"
    )


# ============================================================
# Test 2: Architecture Layer Colors
# ============================================================

def test_layer_colors_are_defined():
    """Ensure every architecture layer has a color."""

    expected_layers = {
        "Domain",
        "Application",
        "Adapters",
        "Dashboard",
        "Bootstrap",
        "Other",
    }

    assert set(LAYER_COLORS) == expected_layers

    assert set(LAYER_ORDER) == expected_layers

    for color in LAYER_COLORS.values():
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7


# ============================================================
# Test 3: Dependency Graph Creation
# ============================================================

def test_create_dependency_figure():
    """
    Verify correct module and dependency rendering.

    Expected:
        3 architectural layer traces
        2 dependency edge traces
        2 directional arrow annotations
    """

    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
    )

    assert isinstance(figure, go.Figure)

    # Three architecture layers are represented.
    layers = module_traces(figure)

    assert len(layers) == 3

    assert {
        trace.name
        for trace in layers
    } == {
        "Domain",
        "Application",
        "Adapters",
    }

    # Two verified dependencies are rendered.
    edges = dependency_traces(figure)

    assert len(edges) == 2

    assert {
        trace.name
        for trace in edges
    } == {
        (
            "archguard.application.scanner "
            "imports archguard.domain.models"
        ),
        (
            "archguard.adapters.parser "
            "imports archguard.domain.models"
        ),
    }

    # Every dependency has a directional arrow.
    assert len(figure.layout.annotations) == 2

    for annotation in figure.layout.annotations:
        assert annotation.showarrow is True


# ============================================================
# Test 4: Architectural Layer Filtering
# ============================================================

def test_filter_architecture_layers():
    """
    Verify selecting specific layers filters both
    modules and their relationships.
    """

    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
        visible_layers=[
            "Domain",
            "Application",
        ],
    )

    displayed_layers = {
        trace.name
        for trace in module_traces(figure)
    }

    assert displayed_layers == {
        "Domain",
        "Application",
    }

    # Only the dependency between the two visible
    # modules should remain.
    edges = dependency_traces(figure)

    assert len(edges) == 1

    assert edges[0].name == (
        "archguard.application.scanner "
        "imports archguard.domain.models"
    )

    assert len(figure.layout.annotations) == 1


# ============================================================
# Test 5: Empty Graph Handling
# ============================================================

def test_empty_graph():
    """Verify an empty project produces a valid figure."""

    figure = create_dependency_figure(
        modules=[],
        dependencies=[],
    )

    assert isinstance(figure, go.Figure)

    assert len(figure.data) == 0

    assert figure.layout.title.text == (
        "No modules match the selected layers"
    )

    assert figure.layout.showlegend is False


# ============================================================
# Test 6: Empty Layer Selection
# ============================================================

def test_empty_layer_selection():
    """
    Verify selecting no architecture layers results
    in an empty visualization.
    """

    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
        visible_layers=[],
    )

    assert isinstance(figure, go.Figure)

    assert len(figure.data) == 0

    assert figure.layout.title.text == (
        "No modules match the selected layers"
    )


# ============================================================
# Test 7: Full Module Names Preserved in Hover
# ============================================================

def test_full_module_names_preserved_in_hover():
    """
    Verify hover information retains full module names.

    Edge traces are excluded because their dependency
    descriptions use the text attribute rather than
    customdata.
    """

    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
    )

    hover_contents = [
        value
        for trace in module_traces(figure)
        for value in trace.customdata
    ]

    assert len(hover_contents) == 3

    for module in sample_modules():
        module_name = module["name"]

        assert any(
            module_name in value
            for value in hover_contents
        )

    assert all(
        "Layer:" in value
        for value in hover_contents
    )

    assert all(
        "Incoming:" in value
        for value in hover_contents
    )

    assert all(
        "Outgoing:" in value
        for value in hover_contents
    )

    # The edge traces still expose their dependencies
    # through their hover templates.
    for trace in dependency_traces(figure):
        assert trace.hovertemplate == (
            "%{text}<extra></extra>"
        )
