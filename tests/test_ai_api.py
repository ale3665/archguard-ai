
"""
ArchGuard AI — FastAPI AI Integration Tests.

Tests:
    - Projects with no findings
    - Verified findings sent to the AI adapter
    - Unavailable Ollama service
    - Workspace security
    - Finding limits

Tests use mocked Ollama responses.
No running LLM is required.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from archguard.adapters.api import create_app
from archguard.adapters.ollama_ai import AIExplanationError


def create_clean_project(tmp_path):
    project = tmp_path / "clean_project"
    project.mkdir()

    (project / "main.py").write_text(
        "def main():\n"
        "    return True\n",
        encoding="utf-8",
    )

    return project


def create_circular_project(tmp_path):
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

    return project


def test_clean_project_skips_ollama(tmp_path):
    create_clean_project(tmp_path)

    client = TestClient(create_app(tmp_path))

    with patch(
        "archguard.adapters.ollama_ai.request.urlopen"
    ) as mocked_request:
        response = client.post(
            "/analyze/explain",
            json={"project_path": "clean_project"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["ai"]["status"] == "no_findings"
    assert data["ai"]["finding_count"] == 0
    assert data["verified_findings"] == []

    mocked_request.assert_not_called()


def test_ai_receives_verified_findings(tmp_path):
    create_circular_project(tmp_path)

    client = TestClient(create_app(tmp_path))

    mocked_result = {
        "status": "success",
        "model": "qwen2.5:7b",
        "explanation": (
            "The verified cycle may increase coupling. "
            "Consider separating shared responsibilities."
        ),
        "finding_count": 1,
    }

    with patch(
        "archguard.adapters.api."
        "OllamaArchitectureAssistant.explain",
        return_value=mocked_result,
    ) as mocked_explain:

        response = client.post(
            "/analyze/explain",
            json={"project_path": "circular_project"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["project_name"] == "circular_project"
    assert data["ai"]["status"] == "success"
    assert data["ai"]["model"] == "qwen2.5:7b"

    rule_ids = {
        finding["rule_id"]
        for finding in data["verified_findings"]
    }

    assert "CIRCULAR_DEPENDENCY" in rule_ids

    # Confirm the model received findings generated
    # by the actual analysis engine.
    kwargs = mocked_explain.call_args.kwargs

    assert kwargs["project_name"] == "circular_project"
    assert kwargs["findings"] == data["verified_findings"]


def test_unavailable_ollama_returns_503(tmp_path):
    create_circular_project(tmp_path)

    client = TestClient(create_app(tmp_path))

    with patch(
        "archguard.adapters.api."
        "OllamaArchitectureAssistant.explain",
        side_effect=AIExplanationError(
            "Connection refused"
        ),
    ):
        response = client.post(
            "/analyze/explain",
            json={"project_path": "circular_project"},
        )

    assert response.status_code == 503

    assert (
        "AI explanation service unavailable"
        in response.json()["detail"]
    )


def test_ai_endpoint_rejects_outside_workspace(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/analyze/explain",
        json={"project_path": ".."},
    )

    assert response.status_code == 403


def test_ai_endpoint_respects_finding_limit(tmp_path):
    create_circular_project(tmp_path)

    client = TestClient(create_app(tmp_path))

    # The API's analysis response is mocked here only
    # to exercise the finding limit independently.
    fake_report = {
        "project_name": "circular_project",
        "summary": {
            "module_count": 2,
            "dependency_count": 2,
            "finding_count": 21,
        },
        "findings": [
            {
                "rule_id": "CIRCULAR_DEPENDENCY",
                "severity": "error",
                "module": f"module_{i}",
                "message": "Test finding",
            }
            for i in range(21)
        ],
    }

    # The endpoint uses its enclosing analyze function,
    # so patch the evaluator at the adapter boundary
    # instead of patching the FastAPI route itself.
    from archguard.domain.models import (
        AnalysisReport,
        ArchitectureFinding,
        Severity,
    )

    fake_analysis = AnalysisReport(
        project_name="circular_project",
        modules=[],
        dependencies=[],
        findings=[
            ArchitectureFinding(
                rule_id=item["rule_id"],
                severity=Severity.ERROR,
                module=item["module"],
                message=item["message"],
            )
            for item in fake_report["findings"]
        ],
    )

    with patch(
        "archguard.adapters.api."
        "ArchitectureEvaluator.evaluate",
        return_value=fake_analysis,
    ), patch(
        "archguard.adapters.api."
        "OllamaArchitectureAssistant.explain"
    ) as mocked_explain:

        response = client.post(
            "/analyze/explain",
            json={"project_path": "circular_project"},
        )

    assert response.status_code == 422
    assert "Maximum: 20" in response.json()["detail"]

    mocked_explain.assert_not_called()
