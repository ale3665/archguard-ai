
"""
ArchGuard AI — Streamlit AI Assistant Tests.

Tests the dashboard's AI communication and display logic.

Uses mocks so tests do not require:
    - A running FastAPI server
    - A running Ollama server
    - Downloaded Qwen model weights
    - An active Streamlit browser session

Run:
    python -m pytest tests/test_dashboard_ai.py -v
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from archguard.dashboard import app as dashboard


# ============================================================
# Test Data
# ============================================================

def sample_findings():
    """Return one verified circular dependency finding."""

    return [
        {
            "rule_id": "CIRCULAR_DEPENDENCY",
            "severity": "error",
            "module": "a",
            "message": (
                "Circular dependency detected among: a, b"
            ),
        },
    ]


def sample_report(findings=None):
    """Return a representative analysis response."""

    if findings is None:
        findings = sample_findings()

    return {
        "project_name": "cycle_demo",
        "summary": {
            "module_count": 2,
            "dependency_count": 2,
            "finding_count": len(findings),
        },
        "modules": [
            {"name": "a"},
            {"name": "b"},
        ],
        "dependencies": [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "a"},
        ],
        "findings": findings,
    }


def sample_ai_response(findings=None):
    """Return a simulated successful Qwen response."""

    if findings is None:
        findings = sample_findings()

    return {
        "project_name": "cycle_demo",
        "analysis_summary": {
            "module_count": 2,
            "dependency_count": 2,
            "finding_count": len(findings),
        },
        "verified_findings": findings,
        "ai": {
            "status": "success",
            "model": "qwen2.5:7b",
            "explanation": (
                "The verified circular dependency between "
                "modules a and b may increase coupling. "
                "Consider extracting shared responsibilities."
            ),
            "finding_count": len(findings),
        },
    }


@pytest.fixture
def mock_streamlit():
    """
    Replace the dashboard's Streamlit dependency with a mock.

    This allows us to test rendering decisions without
    requiring an active Streamlit runtime.
    """

    fake_st = MagicMock()
    fake_st.session_state = {}

    with patch.object(dashboard, "st", fake_st):
        yield fake_st


# ============================================================
# Test 1: Verify AI API communication
# ============================================================

def test_explain_project_calls_correct_endpoint():
    expected_response = sample_ai_response()

    mocked_response = MagicMock()
    mocked_response.json.return_value = expected_response

    with patch.object(
        dashboard.httpx,
        "Client",
    ) as mocked_client_class:

        mocked_client = (
            mocked_client_class
            .return_value
            .__enter__
            .return_value
        )

        mocked_client.post.return_value = mocked_response

        result = dashboard.explain_project_architecture(
            "demo_projects/cycle_demo"
        )

        mocked_client.post.assert_called_once_with(
            f"{dashboard.API_URL}/analyze/explain",
            json={
                "project_path": "demo_projects/cycle_demo",
            },
        )

        mocked_response.raise_for_status.assert_called_once()

        mocked_client_class.assert_called_once_with(
            timeout=180.0,
        )

    assert result == expected_response


# ============================================================
# Test 2: Successful AI response
# ============================================================

def test_successful_ai_explanation_is_stored(
    mock_streamlit,
):
    findings = sample_findings()
    report = sample_report(findings)

    mock_streamlit.button.return_value = True

    expected_response = sample_ai_response(findings)

    with patch.object(
        dashboard,
        "explain_project_architecture",
        return_value=expected_response,
    ) as mocked_explain:

        dashboard.display_ai_assistant(
            report=report,
            analyzed_project_path="demo_projects/cycle_demo",
        )

    mocked_explain.assert_called_once_with(
        "demo_projects/cycle_demo"
    )

    assert (
        mock_streamlit.session_state["ai_explanation"]
        == expected_response
    )

    mock_streamlit.text_area.assert_called_once()

    displayed_text = (
        mock_streamlit.text_area.call_args.kwargs["value"]
    )

    assert "circular dependency" in displayed_text


# ============================================================
# Test 3: No findings disables AI generation
# ============================================================

def test_no_findings_disables_ai_button(
    mock_streamlit,
):
    report = sample_report(findings=[])

    # Simulate no user click.
    mock_streamlit.button.return_value = False

    with patch.object(
        dashboard,
        "explain_project_architecture",
    ) as mocked_explain:

        dashboard.display_ai_assistant(
            report=report,
            analyzed_project_path="demo_projects/cycle_demo",
        )

    mocked_explain.assert_not_called()

    assert (
        mock_streamlit.button.call_args.kwargs["disabled"]
        is True
    )

    mock_streamlit.success.assert_called()


# ============================================================
# Test 4: Ollama unavailable
# ============================================================

def test_ollama_unavailable_is_handled(
    mock_streamlit,
):
    report = sample_report()

    mock_streamlit.button.return_value = True

    request = httpx.Request(
        "POST",
        "http://127.0.0.1:8000/analyze/explain",
    )

    response = httpx.Response(
        503,
        request=request,
        json={
            "detail": "Local AI service unavailable",
        },
    )

    exception = httpx.HTTPStatusError(
        "Service unavailable",
        request=request,
        response=response,
    )

    # An old successful response must not remain visible.
    mock_streamlit.session_state["ai_explanation"] = (
        sample_ai_response()
    )

    with patch.object(
        dashboard,
        "explain_project_architecture",
        side_effect=exception,
    ):

        dashboard.display_ai_assistant(
            report=report,
            analyzed_project_path="demo_projects/cycle_demo",
        )

    mock_streamlit.error.assert_called()

    assert (
        "ai_explanation"
        not in mock_streamlit.session_state
    )


# ============================================================
# Test 5: Backend network failure
# ============================================================

def test_backend_connection_failure_is_handled(
    mock_streamlit,
):
    report = sample_report()

    mock_streamlit.button.return_value = True

    request = httpx.Request(
        "POST",
        "http://127.0.0.1:8000/analyze/explain",
    )

    exception = httpx.ConnectError(
        "Connection refused",
        request=request,
    )

    with patch.object(
        dashboard,
        "explain_project_architecture",
        side_effect=exception,
    ):

        dashboard.display_ai_assistant(
            report=report,
            analyzed_project_path="demo_projects/cycle_demo",
        )

    mock_streamlit.error.assert_called()

    assert (
        "ai_explanation"
        not in mock_streamlit.session_state
    )


# ============================================================
# Test 6: Changed findings trigger a warning
# ============================================================

def test_changed_findings_trigger_warning(
    mock_streamlit,
):
    report = sample_report()

    mock_streamlit.button.return_value = False

    outdated_response = sample_ai_response(
        findings=[]
    )

    mock_streamlit.session_state["ai_explanation"] = (
        outdated_response
    )

    dashboard.display_ai_assistant(
        report=report,
        analyzed_project_path="demo_projects/cycle_demo",
    )

    warning_messages = [
        str(call.args[0])
        for call in mock_streamlit.warning.call_args_list
        if call.args
    ]

    assert any(
        "findings changed" in message.lower()
        for message in warning_messages
    )


# ============================================================
# Test 7: Finding limit disables AI generation
# ============================================================

def test_finding_limit_disables_ai_button(
    mock_streamlit,
):
    findings = sample_findings() * 21

    report = sample_report(
        findings=findings
    )

    mock_streamlit.button.return_value = False

    with patch.object(
        dashboard,
        "explain_project_architecture",
    ) as mocked_explain:

        dashboard.display_ai_assistant(
            report=report,
            analyzed_project_path="demo_projects/cycle_demo",
        )

    assert (
        mock_streamlit.button.call_args.kwargs["disabled"]
        is True
    )

    mocked_explain.assert_not_called()
