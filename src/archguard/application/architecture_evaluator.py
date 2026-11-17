
from archguard.domain.architecture_rules import (
    ArchitectureRule,
    CircularDependencyRule,
    HighCouplingRule,
    LayerBoundaryRule,
)
from archguard.domain.dependency_graph import DependencyGraph
from archguard.domain.models import AnalysisReport, PythonModule


class ArchitectureEvaluator:
    """
    Evaluate Python modules against configurable
    software architecture rules.
    """

    def __init__(
        self,
        rules: list[ArchitectureRule] | None = None,
    ):
        self.rules = (
            list(rules)
            if rules is not None
            else [
                CircularDependencyRule(),
                HighCouplingRule(),
                LayerBoundaryRule(),
            ]
        )

    def evaluate(
        self,
        project_name: str,
        modules: list[PythonModule],
    ) -> AnalysisReport:
        """Build the dependency graph and execute rules."""

        graph = DependencyGraph()
        graph.build(modules)

        findings = []

        for rule in self.rules:
            findings.extend(rule.evaluate(graph))

        return AnalysisReport(
            project_name=project_name,
            modules=list(modules),
            dependencies=graph.get_dependencies(),
            findings=findings,
        )
