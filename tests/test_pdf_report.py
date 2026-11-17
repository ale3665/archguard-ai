
"""
Tests for ArchGuard AI PDF report generation.
"""

from io import BytesIO

import pytest
from pypdf import PdfReader

from archguard.adapters.pdf_report import PDFReportGenerator


def sample_report():
    return {
        "project_name": "SampleProject",
        "summary": {
            "module_count": 2,
            "dependency_count": 2,
            "finding_count": 1,
        },
        "modules": [
            {
                "name": "module_a",
                "path": "module_a.py",
                "classes": [],
                "functions": [],
                "imports": ["module_b"],
            },
            {
                "name": "module_b",
                "path": "module_b.py",
                "classes": [],
                "functions": [],
                "imports": ["module_a"],
            },
        ],
        "dependencies": [
            {"source": "module_a", "target": "module_b"},
            {"source": "module_b", "target": "module_a"},
        ],
        "findings": [
            {
                "rule_id": "CIRCULAR_DEPENDENCY",
                "severity": "error",
                "module": "module_a",
                "message": (
                    "Circular dependency detected among: "
                    "module_a, module_b"
                ),
            },
        ],
    }


def extract_pdf_text(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(
        page.extract_text()
        for page in reader.pages
    )


def test_generate_valid_pdf():
    pdf = PDFReportGenerator().generate(sample_report())

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000

    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) >= 1


def test_pdf_contains_project_information():
    pdf = PDFReportGenerator().generate(sample_report())
    text = extract_pdf_text(pdf)

    assert "ArchGuard AI" in text
    assert "SampleProject" in text
    assert "Executive Summary" in text
    assert "Architecture Metrics" in text


def test_pdf_contains_actual_dependencies():
    pdf = PDFReportGenerator().generate(sample_report())
    text = extract_pdf_text(pdf)

    assert "module_a" in text
    assert "module_b" in text
    assert "Module Dependencies" in text


def test_pdf_contains_findings():
    pdf = PDFReportGenerator().generate(sample_report())
    text = extract_pdf_text(pdf)

    assert "CIRCULAR_DEPENDENCY" in text
    assert "Circular dependency detected" in text
    assert "Architectural Findings" in text


def test_pdf_contains_rule_based_recommendations():
    pdf = PDFReportGenerator().generate(sample_report())
    text = extract_pdf_text(pdf)

    assert "Recommendations" in text
    assert "dependency cycle" in text


def test_generate_report_without_findings():
    report = sample_report()
    report["findings"] = []
    report["summary"]["finding_count"] = 0

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "No architectural findings" in text
    assert "No rule-specific corrective actions" in text


def test_reject_invalid_report_structure():
    generator = PDFReportGenerator()

    with pytest.raises(ValueError):
        generator.generate({"project_name": "Incomplete"})


def test_escaped_special_characters():
    report = sample_report()
    report["project_name"] = "Project <Alpha> & Beta"

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "Project <Alpha> & Beta" in text
