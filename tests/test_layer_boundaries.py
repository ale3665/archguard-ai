
from archguard.application.architecture_evaluator import (
    ArchitectureEvaluator,
)
from archguard.domain.architecture_rules import (
    LayerBoundaryRule,
)
from archguard.domain.dependency_graph import DependencyGraph
from archguard.domain.models import PythonModule, Severity


def test_detect_domain_to_adapter_violation():
    modules = [
        PythonModule(
            name="archguard.domain.models",
            path="archguard/domain/models.py",
            imports=("archguard.adapters.ast_parser",),
        ),
        PythonModule(
            name="archguard.adapters.ast_parser",
            path="archguard/adapters/ast_parser.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    findings = LayerBoundaryRule().evaluate(graph)

    assert len(findings) == 1
    assert findings[0].rule_id == "LAYER_BOUNDARY_VIOLATION"
    assert findings[0].severity == Severity.ERROR
    assert findings[0].module == "archguard.domain.models"


def test_detect_application_to_adapter_violation():
    modules = [
        PythonModule(
            name="archguard.application.scanner",
            path="archguard/application/scanner.py",
            imports=("archguard.adapters.ast_parser",),
        ),
        PythonModule(
            name="archguard.adapters.ast_parser",
            path="archguard/adapters/ast_parser.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    findings = LayerBoundaryRule().evaluate(graph)

    assert len(findings) == 1


def test_allow_valid_dependency_directions():
    modules = [
        PythonModule(
            name="archguard.adapters.parser",
            path="archguard/adapters/parser.py",
            imports=(
                "archguard.application.ports",
                "archguard.domain.models",
            ),
        ),
        PythonModule(
            name="archguard.application.ports",
            path="archguard/application/ports.py",
            imports=("archguard.domain.models",),
        ),
        PythonModule(
            name="archguard.domain.models",
            path="archguard/domain/models.py",
        ),
    ]

    graph = DependencyGraph()
    graph.build(modules)

    findings = LayerBoundaryRule().evaluate(graph)

    assert findings == []


def test_evaluator_includes_boundary_rule():
    modules = [
        PythonModule(
            name="archguard.domain.example",
            path="archguard/domain/example.py",
            imports=("archguard.adapters.storage",),
        ),
        PythonModule(
            name="archguard.adapters.storage",
            path="archguard/adapters/storage.py",
        ),
    ]

    report = ArchitectureEvaluator().evaluate(
        "BoundaryTest",
        modules,
    )

    rule_ids = {
        finding.rule_id
        for finding in report.findings
    }

    assert "LAYER_BOUNDARY_VIOLATION" in rule_ids
