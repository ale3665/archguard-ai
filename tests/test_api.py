
from fastapi.testclient import TestClient

from archguard.adapters.api import create_app


def test_health_endpoint(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


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
        json={"project_path": "sample_project"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["project_name"] == "sample_project"
    assert data["summary"]["module_count"] == 2
    assert data["summary"]["dependency_count"] == 1
    assert data["summary"]["finding_count"] == 0

    assert {
        (item["source"], item["target"])
        for item in data["dependencies"]
    } == {("main", "utils")}


def test_reject_project_outside_workspace(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze",
        json={"project_path": ".."},
    )

    assert response.status_code == 403


def test_reject_nonexistent_project(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze",
        json={"project_path": "missing_project"},
    )

    assert response.status_code == 404


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
        json={"project_path": "circular_project"},
    )

    assert response.status_code == 200

    data = response.json()

    assert any(
        finding["rule_id"] == "CIRCULAR_DEPENDENCY"
        for finding in data["findings"]
    )


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
        json={"project_path": "invalid_project"},
    )

    assert response.status_code == 422
