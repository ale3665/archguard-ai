
import pytest

from archguard.application.project_scanner import ProjectScanner


def test_scan_multiple_python_files(tmp_path):
    (tmp_path / "main.py").write_text(
        "import os\nclass Main:\n    pass\n",
        encoding="utf-8",
    )

    (tmp_path / "utils.py").write_text(
        "def helper():\n    return True\n",
        encoding="utf-8",
    )

    scanner = ProjectScanner()
    modules = scanner.scan(tmp_path)

    assert len(modules) == 2
    assert {module.name for module in modules} == {
        "main",
        "utils",
    }


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

    scanner = ProjectScanner()
    modules = scanner.scan(tmp_path)

    assert len(modules) == 1
    assert modules[0].name == "app"


def test_scan_nested_directory(tmp_path):
    package = tmp_path / "mypackage"
    package.mkdir()

    (package / "module.py").write_text(
        "class Example:\n    pass\n",
        encoding="utf-8",
    )

    scanner = ProjectScanner()
    modules = scanner.scan(tmp_path)

    assert len(modules) == 1
    assert modules[0].name == "mypackage.module"


def test_invalid_project_directory(tmp_path):
    scanner = ProjectScanner()

    with pytest.raises(NotADirectoryError):
        scanner.scan(tmp_path / "nonexistent")
