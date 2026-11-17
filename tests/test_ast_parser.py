
import pytest

from archguard.adapters.ast_parser import ASTSourceCodeParser


# ============================================================
# Test 1: Extract classes, methods, functions, and imports
# ============================================================

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


# ============================================================
# Test 2: Parse an actual Python file
# ============================================================

def test_parse_real_file(tmp_path):
    file_path = tmp_path / "sample.py"

    file_path.write_text(
        "class Example:\n    pass\n",
        encoding="utf-8",
    )

    parser = ASTSourceCodeParser()

    result = parser.parse_file(
        file_path,
        tmp_path,
    )

    assert result.name == "sample"
    assert result.path == "sample.py"
    assert result.classes[0].name == "Example"


# ============================================================
# Test 3: Reject invalid Python syntax
# ============================================================

def test_invalid_python_source():
    parser = ASTSourceCodeParser()

    with pytest.raises(SyntaxError):
        parser.parse_source(
            "def invalid(:",
            module_name="invalid",
            path="invalid.py",
        )


# ============================================================
# Test 4: Reject files outside the project directory
# ============================================================

def test_reject_file_outside_project(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    outside_file = tmp_path / "outside.py"

    outside_file.write_text(
        "x = 1",
        encoding="utf-8",
    )

    parser = ASTSourceCodeParser()

    with pytest.raises(ValueError):
        parser.parse_file(
            outside_file,
            project_root,
        )


# ============================================================
# Test 5: Normalize package initializer names
# ============================================================

def test_package_initializer_name(tmp_path):
    package = tmp_path / "mypackage"
    package.mkdir()

    init_file = package / "__init__.py"

    init_file.write_text(
        "VERSION = '1.0'\n",
        encoding="utf-8",
    )

    parser = ASTSourceCodeParser()

    result = parser.parse_file(
        init_file,
        tmp_path,
    )

    assert result.name == "mypackage"
    assert result.path == "mypackage/__init__.py"


# ============================================================
# Test 6: Normalize nested package initializer names
# ============================================================

def test_nested_package_initializer_name(tmp_path):
    package = tmp_path / "mypackage" / "core"
    package.mkdir(parents=True)

    init_file = package / "__init__.py"

    init_file.write_text(
        "from pathlib import Path\n",
        encoding="utf-8",
    )

    parser = ASTSourceCodeParser()

    result = parser.parse_file(
        init_file,
        tmp_path,
    )

    assert result.name == "mypackage.core"
    assert result.path == "mypackage/core/__init__.py"
    assert result.imports == ("pathlib",)


# ============================================================
# Test 7: Handle an initializer at the project root
# ============================================================

def test_root_initializer_name(tmp_path):
    init_file = tmp_path / "__init__.py"

    init_file.write_text(
        "",
        encoding="utf-8",
    )

    parser = ASTSourceCodeParser()

    result = parser.parse_file(
        init_file,
        tmp_path,
    )

    assert result.name == ""
    assert result.path == "__init__.py"


# ============================================================
# Test 8: Preserve relative import syntax
# ============================================================

def test_relative_import_extraction():
    source = """
from . import utils
from ..core import models
from ...shared.helpers import validate
"""

    parser = ASTSourceCodeParser()

    result = parser.parse_source(
        source,
        module_name="mypackage.subpackage.module",
        path="mypackage/subpackage/module.py",
    )

    assert result.imports == (
        ".",
        "..core",
        "...shared.helpers",
    )
