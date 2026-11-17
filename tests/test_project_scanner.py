
import pytest

from archguard.adapters.ast_parser import ASTSourceCodeParser
from archguard.application.project_scanner import ProjectScanner
from archguard.bootstrap import create_project_scanner


# ============================================================
# Test 1: Scan multiple Python files
# ============================================================

def test_scan_multiple_python_files(tmp_path):
    (tmp_path / "main.py").write_text(
        "import os\nclass Main:\n    pass\n",
        encoding="utf-8",
    )

    (tmp_path / "utils.py").write_text(
        "def helper():\n    return True\n",
        encoding="utf-8",
    )

    scanner = ProjectScanner(parser=ASTSourceCodeParser())
    modules = scanner.scan(tmp_path)

    assert len(modules) == 2
    assert {module.name for module in modules} == {
        "main",
        "utils",
    }


# ============================================================
# Test 2: Skip excluded directories
# ============================================================

def test_skip_excluded_directories(tmp_path):
    (tmp_path / "app.py").write_text(
        "x = 1\n",
        encoding="utf-8",
    )

    venv = tmp_path / ".venv"
    venv.mkdir()

    (venv / "ignored.py").write_text(
        "x = 2\n",
        encoding="utf-8",
    )

    scanner = ProjectScanner(parser=ASTSourceCodeParser())
    modules = scanner.scan(tmp_path)

    assert len(modules) == 1
    assert modules[0].name == "app"


# ============================================================
# Test 3: Scan nested Python packages and directories
# ============================================================

def test_scan_nested_directory(tmp_path):
    package = tmp_path / "mypackage"
    package.mkdir()

    (package / "module.py").write_text(
        "class Example:\n    pass\n",
        encoding="utf-8",
    )

    scanner = ProjectScanner(parser=ASTSourceCodeParser())
    modules = scanner.scan(tmp_path)

    assert len(modules) == 1
    assert modules[0].name == "mypackage.module"
    assert modules[0].classes[0].name == "Example"


# ============================================================
# Test 4: Reject invalid project directories
# ============================================================

def test_invalid_project_directory(tmp_path):
    scanner = ProjectScanner(parser=ASTSourceCodeParser())

    with pytest.raises(NotADirectoryError):
        scanner.scan(tmp_path / "nonexistent")


# ============================================================
# Test 5: Verify dependency injection through bootstrap
# ============================================================

def test_scanner_created_through_bootstrap(tmp_path):
    source_file = tmp_path / "sample.py"

    source_file.write_text(
        "class Sample:\n    pass\n",
        encoding="utf-8",
    )

    # Create the scanner using the composition root.
    scanner = create_project_scanner()

    # Verify the scanner works with the injected AST parser.
    modules = scanner.scan(tmp_path)

    assert isinstance(scanner, ProjectScanner)
    assert len(modules) == 1
    assert modules[0].name == "sample"
    assert modules[0].classes[0].name == "Sample"
