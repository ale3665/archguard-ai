
import pytest

from archguard.adapters.ast_parser import ASTSourceCodeParser


def test_extract_classes_methods_and_functions():
    source = """
import os
from pathlib import Path

class Analyzer(BaseAnalyzer):
    def analyze(self):
        pass

    async def generate_report(self):
        pass

def main():
    pass
"""

    parser = ASTSourceCodeParser()
    result = parser.parse_source(
        source,
        module_name="example",
        path="example.py",
    )

    assert result.name == "example"
    assert result.classes[0].name == "Analyzer"
    assert result.classes[0].methods == (
        "analyze",
        "generate_report",
    )
    assert result.classes[0].bases == ("BaseAnalyzer",)
    assert result.functions == ("main",)
    assert result.imports == ("os", "pathlib")


def test_parse_real_file(tmp_path):
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "class Example:\n    pass\n",
        encoding="utf-8",
    )

    parser = ASTSourceCodeParser()
    result = parser.parse_file(file_path, tmp_path)

    assert result.name == "sample"
    assert result.path == "sample.py"
    assert result.classes[0].name == "Example"


def test_invalid_python_source():
    parser = ASTSourceCodeParser()

    with pytest.raises(SyntaxError):
        parser.parse_source(
            "def invalid(:",
            module_name="invalid",
            path="invalid.py",
        )


def test_reject_file_outside_project(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    outside_file = tmp_path / "outside.py"
    outside_file.write_text("x = 1", encoding="utf-8")

    parser = ASTSourceCodeParser()

    with pytest.raises(ValueError):
        parser.parse_file(outside_file, project_root)
