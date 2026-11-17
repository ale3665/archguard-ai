
import importlib.util
from pathlib import Path

import networkx as nx

from archguard.domain.models import Dependency, PythonModule


class DependencyGraph:
    """
    Represents dependencies between Python project modules.

    Supports:
    - Absolute imports
    - Relative imports
    - Package initializer imports
    - Imported symbols from existing modules
    - Internal dependency filtering
    - Circular dependency detection
    - Module coupling measurement
    """

    def __init__(self):
        self._graph = nx.DiGraph()

    def build(self, modules: list[PythonModule]) -> None:
        """Build a directed graph of internal module dependencies."""

        self._graph.clear()

        module_names = {module.name for module in modules}

        # Register every discovered module.
        for module in modules:
            self._graph.add_node(module.name)

        # Resolve imports to internal project modules.
        for module in modules:
            for imported in module.imports:

                absolute_import = self._make_absolute(
                    imported,
                    module,
                )

                if absolute_import is None:
                    continue

                target = self._resolve_import(
                    absolute_import,
                    module_names,
                )

                if target and target != module.name:
                    self._graph.add_edge(
                        module.name,
                        target,
                    )

    @staticmethod
    def _make_absolute(
        imported: str,
        source_module: PythonModule,
    ) -> str | None:
        """
        Convert a relative import into an absolute module name.

        Example:
            source: package.features.main
            import: ..core.models
            result: package.core.models
        """

        if not imported:
            return None

        # Absolute imports require no transformation.
        if not imported.startswith("."):
            return imported

        # Package initializers represent packages rather
        # than ordinary Python modules.
        is_package = (
            Path(source_module.path).name == "__init__.py"
        )

        if is_package:
            package_name = source_module.name
        else:
            package_name = source_module.name.rpartition(".")[0]

        # A root-level module has no parent package.
        if not package_name:
            return None

        try:
            return importlib.util.resolve_name(
                imported,
                package_name,
            )
        except ImportError:
            # Invalid relative import, such as moving
            # beyond the top-level package.
            return None

    @staticmethod
    def _resolve_import(
        imported: str,
        module_names: set[str],
    ) -> str | None:
        """
        Match an import to an existing project module.

        If an import references a class or function,
        resolve it to the nearest existing parent module.
        """

        # Prefer an exact module match.
        if imported in module_names:
            return imported

        # Example:
        # package.services.Analyzer
        # may refer to a class within package.services.
        parts = imported.split(".")

        for index in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:index])

            if candidate in module_names:
                return candidate

        # Ignore imports that cannot be matched
        # to discovered project modules.
        return None

    def get_dependencies(self) -> list[Dependency]:
        """Return internal dependencies in deterministic order."""

        return [
            Dependency(source=source, target=target)
            for source, target in sorted(self._graph.edges())
        ]

    def get_cycles(self) -> list[list[str]]:
        """Return circular dependency paths."""

        cycles = [
            list(cycle)
            for cycle in nx.simple_cycles(self._graph)
        ]

        return sorted(
            cycles,
            key=lambda cycle: (len(cycle), sorted(cycle)),
        )

    def get_coupling(self) -> dict[str, int]:
        """
        Return outgoing internal dependency counts.

        This measures direct internal fan-out,
        not every possible type of software coupling.
        """

        return {
            module: self._graph.out_degree(module)
            for module in sorted(self._graph.nodes())
        }

    def get_module_count(self) -> int:
        """Return the number of discovered modules."""

        return self._graph.number_of_nodes()

    def get_dependency_count(self) -> int:
        """Return the number of unique internal dependencies."""

        return self._graph.number_of_edges()
