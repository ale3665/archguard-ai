
from archguard.application.architecture_evaluator import (
    ArchitectureEvaluator,
)
from archguard.domain.architecture_rules import (
    CircularDependencyRule,
    HighCouplingRule,
)
from archguard.domain.dependency_graph import DependencyGraph
from archguard.domain.models import PythonModule, Severity


def test_detect_circular_dependency_finding():
    modules = [
        PythonModule(
            name="a", path="a.py", imports=("b",)
        ),
        PythonModule(
            name="b", path="b.py", imports=("a",)
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    findings = CircularDependencyRule().evaluate(graph)

    assert len(findings) == 1
    assert findings[0].rule_id == "CIRCULAR_DEPENDENCY"
    assert findings[0].severity == Severity.ERROR


def test_detect_high_coupling():
    modules = [
        PythonModule(
            name="main",
            path="main.py",
            imports=("a", "b", "c"),
        ),
        PythonModule(name="a", path="a.py"),
        PythonModule(name="b", path="b.py"),
        PythonModule(name="c", path="c.py"),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    findings = HighCouplingRule(threshold=2).evaluate(graph)

    assert len(findings) == 1
    assert findings[0].rule_id == "HIGH_COUPLING"
    assert findings[0].module == "main"


def test_clean_project_has_no_findings():
    modules = [
        PythonModule(
            name="main",
            path="main.py",
            imports=("utils",),
        ),
        PythonModule(name="utils", path="utils.py"),
    ]

    evaluator = ArchitectureEvaluator()
    report = evaluator.evaluate("CleanProject", modules)

    assert report.module_count == 2
    assert report.finding_count == 0
    assert len(report.dependencies) == 1


def test_evaluator_combines_findings():
    modules = [
        PythonModule(
            name="a",
            path="a.py",
            imports=("b", "c", "d"),
        ),
        PythonModule(
            name="b",
            path="b.py",
            imports=("a",),
        ),
        PythonModule(name="c", path="c.py"),
        PythonModule(name="d", path="d.py"),
    ]

    evaluator = ArchitectureEvaluator(
        rules=[
            CircularDependencyRule(),
            HighCouplingRule(threshold=2),
        ]
    )

    report = evaluator.evaluate("TestProject", modules)

    rule_ids = {finding.rule_id for finding in report.findings}

    assert report.module_count == 4
    assert report.finding_count == 2
    assert rule_ids == {
        "CIRCULAR_DEPENDENCY",
        "HIGH_COUPLING",
    }


def test_evaluator_supports_no_rules():
    evaluator = ArchitectureEvaluator(rules=[])

    report = evaluator.evaluate(
        "EmptyRules",
        [PythonModule(name="main", path="main.py")],
    )

    assert report.finding_count == 0
