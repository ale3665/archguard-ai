
from archguard.domain.dependency_graph import DependencyGraph
from archguard.domain.models import PythonModule


def test_build_dependency_graph():
    modules = [
        PythonModule(
            name="main",
            path="main.py",
            imports=("utils", "os"),
        ),
        PythonModule(
            name="utils",
            path="utils.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    assert graph.get_module_count() == 2
    assert graph.get_dependency_count() == 1

    dependencies = graph.get_dependencies()
    assert dependencies[0].source == "main"
    assert dependencies[0].target == "utils"


def test_detect_circular_dependency():
    modules = [
        PythonModule(
            name="module_a",
            path="module_a.py",
            imports=("module_b",),
        ),
        PythonModule(
            name="module_b",
            path="module_b.py",
            imports=("module_a",),
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    cycles = graph.get_cycles()

    assert len(cycles) == 1
    assert set(cycles[0]) == {"module_a", "module_b"}


def test_ignore_external_imports():
    modules = [
        PythonModule(
            name="app",
            path="app.py",
            imports=("os", "json", "requests"),
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    assert graph.get_dependency_count() == 0


def test_calculate_coupling():
    modules = [
        PythonModule(
            name="main",
            path="main.py",
            imports=("utils", "config"),
        ),
        PythonModule(name="utils", path="utils.py"),
        PythonModule(name="config", path="config.py"),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    coupling = graph.get_coupling()

    assert coupling["main"] == 2
    assert coupling["utils"] == 0
    assert coupling["config"] == 0


def test_rebuild_clears_previous_graph():
    graph = DependencyGraph()

    graph.build([
        PythonModule(name="first", path="first.py"),
    ])

    graph.build([
        PythonModule(name="second", path="second.py"),
    ])

    assert graph.get_module_count() == 1
    assert graph.get_dependency_count() == 0
