
import ast
from pathlib import Path

from archguard.domain.models import PythonClass, PythonModule


class ASTSourceCodeParser:
    """
    Extract structural information from Python source files.

    Features:
    - Python module identification
    - Package initializer normalization
    - Class and method extraction
    - Top-level function extraction
    - Inheritance extraction
    - Absolute and relative import extraction
    - Imported name preservation
    - Project directory boundary validation

    The analyzed source code is never executed.
    """

    def parse_file(
        self,
        file_path: str | Path,
        project_root: str | Path,
    ) -> PythonModule:
        """Parse a Python source file inside the project directory."""

        file_path = Path(file_path).resolve()
        project_root = Path(project_root).resolve()

        # Prevent analysis of files outside the project.
        if not file_path.is_relative_to(project_root):
            raise ValueError(
                "File is outside the project directory"
            )

        # Only Python source files are supported.
        if file_path.suffix != ".py":
            raise ValueError(
                "Only Python files are supported"
            )

        # Read source code without executing it.
        source = file_path.read_text(encoding="utf-8")

        relative_path = file_path.relative_to(project_root)

        # Convert the file path into module name components.
        module_parts = list(
            relative_path.with_suffix("").parts
        )

        # Normalize package initializer names.
        # Example:
        # archguard/domain/__init__.py
        # becomes archguard.domain
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
        Extract structural information from Python source code.

        Parameters:
            source: Python source code as a string.
            module_name: Fully qualified module name.
            path: Relative path of the source file.

        Returns:
            PythonModule containing extracted structural data.

        Raises:
            SyntaxError: If the source contains invalid Python syntax.
        """

        tree = ast.parse(source, filename=path)

        classes: list[PythonClass] = []
        functions: list[str] = []
        imports: list[str] = []

        # --------------------------------------------------
        # Extract module-level classes and functions.
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Extract absolute and relative imports.
        # --------------------------------------------------

        for node in ast.walk(tree):

            # Example:
            # import os
            # import package.module
            if isinstance(node, ast.Import):

                imports.extend(
                    alias.name
                    for alias in node.names
                )

            # Examples:
            # from pathlib import Path
            # from . import utils
            # from ..core import models
            # from .services import Analyzer
            elif isinstance(node, ast.ImportFrom):

                prefix = "." * node.level
                module = node.module or ""

                # Preserve the imported module or package.
                base_import = prefix + module

                if module:
                    imports.append(base_import)

                # Preserve individual imported names.
                for alias in node.names:

                    # Wildcard imports do not provide an
                    # explicit imported symbol name.
                    if alias.name == "*":
                        if not module:
                            imports.append(base_import)
                        continue

                    # Example:
                    # from .services import Analyzer
                    # -> .services
                    # -> .services.Analyzer
                    if module:
                        imports.append(
                            f"{base_import}.{alias.name}"
                        )

                    # Example:
                    # from . import utils
                    # -> .utils
                    else:
                        imports.append(
                            f"{prefix}{alias.name}"
                        )

        return PythonModule(
            name=module_name,
            path=path,
            classes=tuple(classes),
            functions=tuple(functions),
            imports=tuple(imports),
        )
