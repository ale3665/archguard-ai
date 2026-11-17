
import ast
from pathlib import Path

from archguard.domain.models import PythonClass, PythonModule


class ASTSourceCodeParser:
    """Extracts structural information from Python source files."""

    def parse_file(
        self,
        file_path: str | Path,
        project_root: str | Path,
    ) -> PythonModule:
        file_path = Path(file_path).resolve()
        project_root = Path(project_root).resolve()

        if not file_path.is_relative_to(project_root):
            raise ValueError("File is outside the project directory")

        if file_path.suffix != ".py":
            raise ValueError("Only Python files are supported")

        source = file_path.read_text(encoding="utf-8")
        return self.parse_source(
            source,
            module_name=file_path.relative_to(project_root)
            .with_suffix("")
            .as_posix()
            .replace("/", "."),
            path=file_path.relative_to(project_root).as_posix(),
        )

    def parse_source(
        self,
        source: str,
        module_name: str,
        path: str,
    ) -> PythonModule:
        tree = ast.parse(source, filename=path)

        classes = []
        functions = []
        imports = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = tuple(
                    child.name
                    for child in node.body
                    if isinstance(
                        child, (ast.FunctionDef, ast.AsyncFunctionDef)
                    )
                )

                bases = tuple(
                    ast.unparse(base) for base in node.bases
                )

                classes.append(
                    PythonClass(
                        name=node.name,
                        methods=methods,
                        bases=bases,
                    )
                )

            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                functions.append(node.name)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(
                    alias.name for alias in node.names
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
