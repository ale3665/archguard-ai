
"""
Integration tests for the ArchGuard AI FastAPI backend.

Endpoints tested:
    GET  /
    GET  /health
    POST /analyze

Run tests:
    python -m pytest tests/test_api.py -v
"""

from fastapi.testclient import TestClient

from archguard.adapters.api import create_app


# ============================================================
# Test 1: Verify the ArchGuard AI homepage
# ============================================================

def test_homepage_endpoint(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["application"] == "ArchGuard AI"
    assert data["status"] == "running"
    assert data["version"] == "0.1.0"

    assert data["endpoints"]["home"] == "/"
    assert data["endpoints"]["health"] == "/health"
    assert data["endpoints"]["analyze"] == "/analyze"
    assert data["endpoints"]["documentation"] == "/docs"
    assert data["endpoints"]["openapi"] == "/openapi.json"


# ============================================================
# Test 2: Verify the API health endpoint
# ============================================================

def test_health_endpoint(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["application"] == "ArchGuard AI"


# ============================================================
# Test 3: Analyze a valid Python project
# ============================================================

def test_analyze_python_project(tmp_path):
    project = tmp_path / "sample_project"
    project.mkdir()

    (project / "main.py").write_text(
        "import utils\n"
        "class Main:\n"
        "    def run(self):\n"
        "        pass\n",
        encoding="utf-8",
    )

    (project / "utils.py").write_text(
        "def helper():\n"
        "    return True\n",
        encoding="utf-8",
    )

    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze",
        json={
            "project_path": "sample_project",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["project_name"] == "sample_project"

    summary = data["summary"]

    assert summary["module_count"] == 2
    assert summary["dependency_count"] == 1
    assert summary["finding_count"] == 0

    module_names = {
        module["name"]
        for module in data["modules"]
    }

    assert module_names == {
        "main",
        "utils",
    }

    dependencies = {
        (dependency["source"], dependency["target"])
        for dependency in data["dependencies"]
    }

    assert dependencies == {
        ("main", "utils"),
    }

    main_module = next(
        module
        for module in data["modules"]
        if module["name"] == "main"
    )

    assert main_module["path"] == "main.py"
    assert main_module["imports"] == ["utils"]
    assert main_module["classes"][0]["name"] == "Main"
    assert main_module["classes"][0]["methods"] == ["run"]


# ============================================================
# Test 4: Reject project paths outside the allowed workspace
# ============================================================

def test_reject_project_outside_workspace(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze",
        json={
            "project_path": "..",
        },
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Project is outside the allowed workspace."
    )


# ============================================================
# Test 5: Reject nonexistent project directories
# ============================================================

def test_reject_nonexistent_project(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze",
        json={
            "project_path": "missing_project",
        },
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Project directory not found."
    )


# ============================================================
# Test 6: Detect circular dependencies through the API
# ============================================================

def test_report_architectural_finding(tmp_path):
    project = tmp_path / "circular_project"
    project.mkdir()

    (project / "a.py").write_text(
        "import b\n",
        encoding="utf-8",
    )

    (project / "b.py").write_text(
        "import a\n",
        encoding="utf-8",
    )

    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze",
        json={
            "project_path": "circular_project",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["module_count"] == 2
    assert data["summary"]["dependency_count"] == 2
    assert data["summary"]["finding_count"] >= 1

    circular_findings = [
        finding
        for finding in data["findings"]
        if finding["rule_id"] == "CIRCULAR_DEPENDENCY"
    ]

    assert len(circular_findings) == 1

    finding = circular_findings[0]

    assert finding["severity"] == "error"
    assert "Circular dependency" in finding["message"]


# ============================================================
# Test 7: Reject invalid Python syntax
# ============================================================

def test_reject_invalid_python_source(tmp_path):
    project = tmp_path / "invalid_project"
    project.mkdir()

    (project / "broken.py").write_text(
        "def broken(:\n",
        encoding="utf-8",
    )

    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze",
        json={
            "project_path": "invalid_project",
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert "Unable to analyze project" in data["detail"]
