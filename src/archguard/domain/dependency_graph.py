
import networkx as nx

from archguard.domain.models import Dependency, PythonModule


class DependencyGraph:
    """Represents dependencies between Python project modules."""

    def __init__(self):
        self._graph = nx.DiGraph()

    def build(self, modules: list[PythonModule]) -> None:
        """Build a graph using only internal project dependencies."""
        self._graph.clear()

        module_names = {module.name for module in modules}

        for module in modules:
            self._graph.add_node(module.name)

        for module in modules:
            for imported in module.imports:
                target = self._resolve_import(imported, module_names)

                if target and target != module.name:
                    self._graph.add_edge(module.name, target)

    @staticmethod
    def _resolve_import(
        imported: str,
        module_names: set[str],
    ) -> str | None:
        """Resolve an absolute import to an internal module."""
        if imported.startswith("."):
            return None

        if imported in module_names:
            return imported

        matches = [
            name
            for name in module_names
            if imported.startswith(name + ".")
        ]

        if matches:
            return max(matches, key=len)

        return None

    def get_dependencies(self) -> list[Dependency]:
        return [
            Dependency(source=source, target=target)
            for source, target in sorted(self._graph.edges())
        ]

    def get_cycles(self) -> list[list[str]]:
        return [
            list(cycle)
            for cycle in nx.simple_cycles(self._graph)
        ]

    def get_coupling(self) -> dict[str, int]:
        """Return outgoing dependency count for each module."""
        return {
            module: self._graph.out_degree(module)
            for module in self._graph.nodes()
        }

    def get_module_count(self) -> int:
        return self._graph.number_of_nodes()

    def get_dependency_count(self) -> int:
        return self._graph.number_of_edges()
