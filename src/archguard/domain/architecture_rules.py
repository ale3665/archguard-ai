
from abc import ABC, abstractmethod

from archguard.domain.dependency_graph import DependencyGraph
from archguard.domain.models import ArchitectureFinding, Severity


class ArchitectureRule(ABC):
    """Abstract base class for architecture evaluation rules."""

    @abstractmethod
    def evaluate(
        self, graph: DependencyGraph
    ) -> list[ArchitectureFinding]:
        """Evaluate a graph and return architectural findings."""
        ...


class CircularDependencyRule(ArchitectureRule):
    """Detects circular module dependencies."""

    RULE_ID = "CIRCULAR_DEPENDENCY"

    def evaluate(
        self, graph: DependencyGraph
    ) -> list[ArchitectureFinding]:
        findings = []

        for cycle in graph.get_cycles():
            ordered_cycle = sorted(cycle)

            findings.append(
                ArchitectureFinding(
                    rule_id=self.RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        "Circular dependency detected among: "
                        + ", ".join(ordered_cycle)
                    ),
                    module=ordered_cycle[0],
                )
            )

        return findings


class HighCouplingRule(ArchitectureRule):
    """Detects modules with excessive outgoing dependencies."""

    RULE_ID = "HIGH_COUPLING"

    def __init__(self, threshold: int = 3):
        if threshold < 0:
            raise ValueError("Threshold must be nonnegative")

        self.threshold = threshold

    def evaluate(
        self, graph: DependencyGraph
    ) -> list[ArchitectureFinding]:
        findings = []

        coupling = graph.get_coupling()

        for module, count in sorted(coupling.items()):
            if count > self.threshold:
                findings.append(
                    ArchitectureFinding(
                        rule_id=self.RULE_ID,
                        severity=Severity.WARNING,
                        message=(
                            f"Module '{module}' depends on "
                            f"{count} internal modules. "
                            f"Configured threshold: {self.threshold}."
                        ),
                        module=module,
                    )
                )

        return findings
