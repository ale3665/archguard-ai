
"""
Tests for the optional Ollama architecture assistant.

All HTTP interactions are mocked.
A running Ollama server is not required.
"""

import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import URLError

import pytest

from archguard.adapters.ollama_ai import (
    AIExplanationError,
    OllamaArchitectureAssistant,
)


def sample_findings():
    return [
        {
            "rule_id": "CIRCULAR_DEPENDENCY",
            "severity": "error",
            "module": "package.a",
            "message": (
                "Circular dependency detected among: "
                "package.a, package.b"
            ),
        }
    ]


def test_default_configuration(monkeypatch):
    monkeypatch.delenv(
        "ARCHGUARD_OLLAMA_MODEL",
        raising=False,
    )
    monkeypatch.delenv(
        "ARCHGUARD_OLLAMA_URL",
        raising=False,
    )

    assistant = OllamaArchitectureAssistant()

    assert assistant.model == "qwen2.5:7b"
    assert assistant.base_url == "http://127.0.0.1:11434"


def test_custom_model():
    assistant = OllamaArchitectureAssistant(
        model="custom-qwen",
    )

    assert assistant.model == "custom-qwen"


def test_reject_remote_endpoint():
    with pytest.raises(ValueError):
        OllamaArchitectureAssistant(
            base_url="https://external.example.com",
        )


def test_prompt_contains_verified_findings():
    assistant = OllamaArchitectureAssistant()

    prompt = assistant.build_prompt(
        "SampleProject",
        sample_findings(),
    )

    assert "SampleProject" in prompt
    assert "CIRCULAR_DEPENDENCY" in prompt
    assert "package.a" in prompt
    assert "Do not invent modules" in prompt


def test_no_findings_skips_ollama():
    assistant = OllamaArchitectureAssistant()

    with patch(
        "archguard.adapters.ollama_ai.request.urlopen"
    ) as mocked_request:
        result = assistant.explain(
            "SampleProject",
            [],
        )

    mocked_request.assert_not_called()

    assert result["status"] == "no_findings"
    assert result["finding_count"] == 0


def test_successful_ai_explanation():
    assistant = OllamaArchitectureAssistant()

    response_data = {
        "response": (
            "The circular dependency may increase coupling."
        )
    }

    mocked_response = BytesIO(
        json.dumps(response_data).encode("utf-8")
    )

    with patch(
        "archguard.adapters.ollama_ai.request.urlopen"
    ) as mocked_request:
        mocked_request.return_value.__enter__.return_value = (
            mocked_response
        )

        result = assistant.explain(
            "SampleProject",
            sample_findings(),
        )

        sent_request = mocked_request.call_args.args[0]
        payload = json.loads(
            sent_request.data.decode("utf-8")
        )

    assert result["status"] == "success"
    assert result["model"] == "qwen2.5:7b"
    assert result["finding_count"] == 1
    assert "circular dependency" in result["explanation"]

    assert payload["stream"] is False
    assert payload["model"] == "qwen2.5:7b"


def test_ollama_connection_failure():
    assistant = OllamaArchitectureAssistant()

    with patch(
        "archguard.adapters.ollama_ai.request.urlopen",
        side_effect=URLError("Connection refused"),
    ):
        with pytest.raises(AIExplanationError):
            assistant.explain(
                "SampleProject",
                sample_findings(),
            )


def test_empty_ai_response():
    assistant = OllamaArchitectureAssistant()

    mocked_response = BytesIO(
        json.dumps({"response": ""}).encode("utf-8")
    )

    with patch(
        "archguard.adapters.ollama_ai.request.urlopen"
    ) as mocked_request:
        mocked_request.return_value.__enter__.return_value = (
            mocked_response
        )

        with pytest.raises(
            AIExplanationError,
            match="empty explanation",
        ):
            assistant.explain(
                "SampleProject",
                sample_findings(),
            )


def test_reject_excessive_findings():
    assistant = OllamaArchitectureAssistant()

    findings = sample_findings() * 21

    with pytest.raises(ValueError):
        assistant.explain(
            "SampleProject",
            findings,
        )
