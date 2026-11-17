
from archguard.domain.dependency_graph import DependencyGraph
from archguard.domain.models import PythonModule


# ============================================================
# Test 1: Build a dependency graph
# ============================================================

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

    assert len(dependencies) == 1
    assert dependencies[0].source == "main"
    assert dependencies[0].target == "utils"


# ============================================================
# Test 2: Detect a circular dependency
# ============================================================

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


# ============================================================
# Test 3: Ignore external imports
# ============================================================

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


# ============================================================
# Test 4: Calculate outgoing module coupling
# ============================================================

def test_calculate_coupling():
    modules = [
        PythonModule(
            name="main",
            path="main.py",
            imports=("utils", "config"),
        ),
        PythonModule(
            name="utils",
            path="utils.py",
        ),
        PythonModule(
            name="config",
            path="config.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    coupling = graph.get_coupling()

    assert coupling["main"] == 2
    assert coupling["utils"] == 0
    assert coupling["config"] == 0


# ============================================================
# Test 5: Rebuilding clears previous graph data
# ============================================================

def test_rebuild_clears_previous_graph():
    graph = DependencyGraph()

    graph.build([
        PythonModule(
            name="first",
            path="first.py",
        ),
    ])

    graph.build([
        PythonModule(
            name="second",
            path="second.py",
        ),
    ])

    assert graph.get_module_count() == 1
    assert graph.get_dependency_count() == 0

    assert set(graph.get_coupling()) == {"second"}


# ============================================================
# Test 6: Resolve a sibling module through relative import
# ============================================================

def test_resolve_sibling_relative_import():
    modules = [
        PythonModule(
            name="package.main",
            path="package/main.py",
            imports=(".utils",),
        ),
        PythonModule(
            name="package.utils",
            path="package/utils.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    dependencies = graph.get_dependencies()

    assert len(dependencies) == 1
    assert dependencies[0].source == "package.main"
    assert dependencies[0].target == "package.utils"


# ============================================================
# Test 7: Resolve imports from a parent package
# ============================================================

def test_resolve_parent_relative_import():
    modules = [
        PythonModule(
            name="package.features.handler",
            path="package/features/handler.py",
            imports=(
                "..core",
                "..core.models",
            ),
        ),
        PythonModule(
            name="package.core",
            path="package/core/__init__.py",
        ),
        PythonModule(
            name="package.core.models",
            path="package/core/models.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    dependencies = {
        (item.source, item.target)
        for item in graph.get_dependencies()
    }

    assert dependencies == {
        (
            "package.features.handler",
            "package.core",
        ),
        (
            "package.features.handler",
            "package.core.models",
        ),
    }


# ============================================================
# Test 8: Resolve relative imports inside package initializers
# ============================================================

def test_relative_import_from_package_initializer():
    modules = [
        PythonModule(
            name="package.feature",
            path="package/feature/__init__.py",
            imports=(".helper",),
        ),
        PythonModule(
            name="package.feature.helper",
            path="package/feature/helper.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    dependencies = graph.get_dependencies()

    assert len(dependencies) == 1
    assert dependencies[0].source == "package.feature"
    assert dependencies[0].target == "package.feature.helper"


# ============================================================
# Test 9: Resolve imported classes to their parent module
# ============================================================

def test_resolve_imported_class_to_module():
    modules = [
        PythonModule(
            name="package.main",
            path="package/main.py",
            imports=(
                "package.services",
                "package.services.Analyzer",
            ),
        ),
        PythonModule(
            name="package.services",
            path="package/services.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    dependencies = graph.get_dependencies()

    assert len(dependencies) == 1
    assert dependencies[0].source == "package.main"
    assert dependencies[0].target == "package.services"


# ============================================================
# Test 10: Detect circular dependencies with relative imports
# ============================================================

def test_circular_dependency_with_relative_imports():
    modules = [
        PythonModule(
            name="package.a",
            path="package/a.py",
            imports=(".b",),
        ),
        PythonModule(
            name="package.b",
            path="package/b.py",
            imports=(".a",),
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    cycles = graph.get_cycles()

    assert len(cycles) == 1
    assert set(cycles[0]) == {
        "package.a",
        "package.b",
    }


# ============================================================
# Test 11: Ignore invalid relative imports
# ============================================================

def test_ignore_invalid_relative_imports():
    modules = [
        PythonModule(
            name="package.main",
            path="package/main.py",
            imports=("...outside",),
        ),
        PythonModule(
            name="outside",
            path="outside.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    assert graph.get_dependency_count() == 0
