
from pathlib import Path
from typing import Protocol

from archguard.domain.models import PythonModule


class SourceCodeParser(Protocol):
    """Contract for parsing Python source files."""

    def parse_file(
        self,
        file_path: str | Path,
        project_root: str | Path,
    ) -> PythonModule:
        ...
