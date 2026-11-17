
from abc import ABC, abstractmethod

from archguard.domain.dependency_graph import DependencyGraph
from archguard.domain.models import ArchitectureFinding, Severity


class ArchitectureRule(ABC):
    """
    Abstract base class for software architecture rules.

    Every architectural rule must implement evaluate()
    and return a list of structured findings.

    This abstraction supports the Strategy design pattern
    and the Open/Closed Principle.
    """

    @abstractmethod
    def evaluate(
        self,
        graph: DependencyGraph,
    ) -> list[ArchitectureFinding]:
        """Evaluate a dependency graph and return findings."""
        ...


class CircularDependencyRule(ArchitectureRule):
    """
    Detect circular dependencies between Python modules.

    Circular dependencies can indicate excessive coupling
    and may reduce software maintainability.
    """

    RULE_ID = "CIRCULAR_DEPENDENCY"

    def evaluate(
        self,
        graph: DependencyGraph,
    ) -> list[ArchitectureFinding]:
        """Identify circular module dependencies."""

        findings: list[ArchitectureFinding] = []

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
    """
    Identify modules with excessive outgoing dependencies.

    Coupling is measured as the number of distinct internal
    modules that a module directly depends on.

    A module is flagged when its coupling count exceeds
    the configured threshold.
    """

    RULE_ID = "HIGH_COUPLING"

    def __init__(
        self,
        threshold: int = 3,
    ):
        if threshold < 0:
            raise ValueError(
                "Threshold must be nonnegative"
            )

        self.threshold = threshold

    def evaluate(
        self,
        graph: DependencyGraph,
    ) -> list[ArchitectureFinding]:
        """Identify modules exceeding the coupling threshold."""

        findings: list[ArchitectureFinding] = []

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
                            f"Configured threshold: "
                            f"{self.threshold}."
                        ),
                        module=module,
                    )
                )

        return findings


class LayerBoundaryRule(ArchitectureRule):
    """
    Enforce dependency boundaries in ArchGuard's
    Hexagonal Architecture.

    Architectural constraints:

    1. Domain must not depend on Application or Adapters.
    2. Application must not depend on concrete Adapters.
    3. Adapters may depend on Application and Domain.
    4. Domain may depend on other Domain components.
    5. Application may depend on Domain components.

    Violations are reported as ERROR severity.

    The package root is configurable, allowing this rule
    to be reused with similarly structured Python projects.
    """

    RULE_ID = "LAYER_BOUNDARY_VIOLATION"

    def __init__(
        self,
        package_root: str = "archguard",
    ):
        if not package_root or not package_root.strip(". "):
            raise ValueError(
                "Package root cannot be empty"
            )

        self.package_root = package_root.strip(". ")

        # Define forbidden cross-layer dependencies.
        self.forbidden_dependencies: dict[str, set[str]] = {
            "domain": {
                "application",
                "adapters",
                "dashboard",
                "bootstrap",
            },
            "application": {
                "adapters",
                "dashboard",
                "bootstrap",
            },
        }

    def _get_layer(
        self,
        module_name: str,
    ) -> str | None:
        """
        Identify the architectural layer for a module.

        Example:
            archguard.domain.models -> domain
            archguard.application.ports -> application
            archguard.adapters.ast_parser -> adapters
        """

        prefix = self.package_root + "."

        if not module_name.startswith(prefix):
            return None

        relative_name = module_name[len(prefix):]

        if not relative_name:
            return None

        return relative_name.split(".")[0]

    def evaluate(
        self,
        graph: DependencyGraph,
    ) -> list[ArchitectureFinding]:
        """Detect forbidden dependencies between layers."""

        findings: list[ArchitectureFinding] = []

        for dependency in graph.get_dependencies():

            source_layer = self._get_layer(
                dependency.source
            )

            target_layer = self._get_layer(
                dependency.target
            )

            # Ignore modules outside the configured package.
            if source_layer is None or target_layer is None:
                continue

            forbidden_targets = self.forbidden_dependencies.get(
                source_layer,
                set(),
            )

            if target_layer in forbidden_targets:

                findings.append(
                    ArchitectureFinding(
                        rule_id=self.RULE_ID,
                        severity=Severity.ERROR,
                        message=(
                            "Forbidden architectural dependency: "
                            f"'{dependency.source}' depends on "
                            f"'{dependency.target}'. "
                            f"The '{source_layer}' layer must not "
                            f"depend on the '{target_layer}' layer."
                        ),
                        module=dependency.source,
                    )
                )

        return findings
