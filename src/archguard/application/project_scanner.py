
from pathlib import Path

from archguard.adapters.ast_parser import ASTSourceCodeParser
from archguard.domain.models import PythonModule


class ProjectScanner:
    """Discovers and analyzes Python files within a project."""

    EXCLUDED_DIRECTORIES = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "build",
        "dist",
    }

    def __init__(self, parser: ASTSourceCodeParser | None = None):
        self.parser = parser or ASTSourceCodeParser()

    def scan(self, project_root: str | Path) -> list[PythonModule]:
        root = Path(project_root).resolve()

        if not root.is_dir():
            raise NotADirectoryError(
                f"Invalid project directory: {root}"
            )

        modules = []

        for file_path in sorted(root.rglob("*.py")):
            relative = file_path.relative_to(root)

            if any(
                part in self.EXCLUDED_DIRECTORIES
                for part in relative.parts[:-1]
            ):
                continue

            if file_path.is_symlink():
                continue

            module = self.parser.parse_file(file_path, root)
            modules.append(module)

        return modules
