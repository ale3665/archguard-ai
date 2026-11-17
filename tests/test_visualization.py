
"""
Tests for ArchGuard AI's architecture visualization.
"""

from archguard.dashboard.visualization import (
    LAYER_COLORS,
    classify_module,
    create_dependency_figure,
)


def sample_modules():
    return [
        {"name": "archguard.domain.models"},
        {"name": "archguard.application.scanner"},
        {"name": "archguard.adapters.parser"},
    ]


def sample_dependencies():
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


def test_classify_architecture_layers():
    assert classify_module(
        "archguard.domain.models"
    ) == "Domain"

    assert classify_module(
        "archguard.application.scanner"
    ) == "Application"

    assert classify_module(
        "archguard.adapters.parser"
    ) == "Adapters"

    assert classify_module(
        "archguard.dashboard.app"
    ) == "Dashboard"

    assert classify_module(
        "archguard.bootstrap"
    ) == "Bootstrap"

    assert classify_module(
        "other.project"
    ) == "Other"


def test_layer_colors_are_defined():
    assert len(LAYER_COLORS) == 6

    assert LAYER_COLORS["Domain"] == "#16A34A"
    assert LAYER_COLORS["Application"] == "#D97706"
    assert LAYER_COLORS["Adapters"] == "#2563EB"


def test_create_dependency_figure():
    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
    )

    assert len(figure.data) == 3

    assert len(figure.layout.annotations) == 2

    displayed_layers = {
        trace.name for trace in figure.data
    }

    assert displayed_layers == {
        "Domain",
        "Application",
        "Adapters",
    }


def test_filter_architecture_layers():
    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
        visible_layers=["Domain", "Application"],
    )

    displayed_layers = {
        trace.name for trace in figure.data
    }

    assert displayed_layers == {
        "Domain",
        "Application",
    }

    # Only the Application -> Domain edge remains.
    assert len(figure.layout.annotations) == 1


def test_empty_graph():
    figure = create_dependency_figure(
        modules=[],
        dependencies=[],
    )

    assert len(figure.data) == 0


def test_empty_layer_selection():
    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
        visible_layers=[],
    )

    assert len(figure.data) == 0


def test_full_module_names_preserved_in_hover():
    figure = create_dependency_figure(
        sample_modules(),
        sample_dependencies(),
    )

    hover_contents = [
        value
        for trace in figure.data
        for value in trace.customdata
    ]

    assert any(
        "archguard.domain.models" in value
        for value in hover_contents
    )
