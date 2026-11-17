
import ast
from pathlib import Path

from archguard.domain.models import PythonClass, PythonModule


class ASTSourceCodeParser:
    """
    Extracts structural information from Python source files.

    Supports:
    - Python module identification
    - Package name normalization
    - Class and method extraction
    - Function extraction
    - Inheritance relationships
    - Absolute and relative import extraction
    - Project directory boundary validation
    """

    def parse_file(
        self,
        file_path: str | Path,
        project_root: str | Path,
    ) -> PythonModule:
        """Parse a Python file located inside a project directory."""

        file_path = Path(file_path).resolve()
        project_root = Path(project_root).resolve()

        # Ensure the file belongs to the selected project.
        if not file_path.is_relative_to(project_root):
            raise ValueError(
                "File is outside the project directory"
            )

        # Only Python files can be analyzed.
        if file_path.suffix != ".py":
            raise ValueError(
                "Only Python files are supported"
            )

        # Read the Python source without executing it.
        source = file_path.read_text(encoding="utf-8")

        relative_path = file_path.relative_to(project_root)

        # Convert the relative file path into Python module parts.
        module_parts = list(
            relative_path.with_suffix("").parts
        )

        # Normalize package initializer names.
        # Example:
        # archguard/domain/__init__.py
        # becomes:
        # archguard.domain
        if module_parts[-1] == "__init__":
            module_parts.pop()

        module_name = ".".join(module_parts)

        return self.parse_source(
            source=source,
            module_name=module_name,
            path=relative_path.as_posix(),
        )

    def parse_source(
        self,
        source: str,
        module_name: str,
        path: str,
    ) -> PythonModule:
        """
        Parse Python source code into structured domain models.

        The source code is never executed.
        """

        tree = ast.parse(source, filename=path)

        classes = []
        functions = []
        imports = []

        # Extract module-level classes and functions.
        for node in tree.body:

            if isinstance(node, ast.ClassDef):

                methods = tuple(
                    child.name
                    for child in node.body
                    if isinstance(
                        child,
                        (
                            ast.FunctionDef,
                            ast.AsyncFunctionDef,
                        ),
                    )
                )

                bases = tuple(
                    ast.unparse(base)
                    for base in node.bases
                )

                classes.append(
                    PythonClass(
                        name=node.name,
                        methods=methods,
                        bases=bases,
                    )
                )

            elif isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                functions.append(node.name)

        # Extract imports throughout the syntax tree.
        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                imports.extend(
                    alias.name
                    for alias in node.names
                )

            elif isinstance(node, ast.ImportFrom):
                prefix = "." * node.level
                module = node.module or ""

                imports.append(prefix + module)

        return PythonModule(
            name=module_name,
            path=path,
            classes=tuple(classes),
            functions=tuple(functions),
            imports=tuple(imports),
        )
