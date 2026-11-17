
"""
ArchGuard AI — PDF Report Generation Tests.

Tests the professional PDF architecture reporting adapter.

Coverage:
    - Valid PDF generation
    - Project identification and report sections
    - Internal dependency reporting
    - Architectural findings
    - Deterministic recommendations
    - Reports without findings
    - Invalid report structure
    - Special character escaping
    - Extended architecture metrics
    - Dependency table pagination
    - Large multipage reports

Run:
    python -m pytest tests/test_pdf_report.py -v
"""

from io import BytesIO

import pytest
from pypdf import PdfReader

from archguard.adapters.pdf_report import PDFReportGenerator


# ============================================================
# Test Fixtures and Helpers
# ============================================================

def sample_report() -> dict:
    """Create a representative architecture analysis report."""

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
            {
                "source": "module_a",
                "target": "module_b",
            },
            {
                "source": "module_b",
                "target": "module_a",
            },
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


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract and normalize text from every PDF page.

    Whitespace normalization prevents tests from failing
    when PDF text extraction introduces line breaks.
    """

    reader = PdfReader(BytesIO(pdf_bytes))

    combined = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    return " ".join(combined.split())


# ============================================================
# Test 1: Generate a valid PDF
# ============================================================

def test_generate_valid_pdf():
    report = sample_report()

    pdf = PDFReportGenerator().generate(report)

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000

    reader = PdfReader(BytesIO(pdf))

    assert len(reader.pages) >= 1


# ============================================================
# Test 2: Verify project identification and report sections
# ============================================================

def test_pdf_contains_project_information():
    report = sample_report()

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "ArchGuard AI" in text
    assert "SampleProject" in text
    assert "Executive Summary" in text
    assert "Architecture Metrics" in text
    assert "Module Dependencies" in text
    assert "Architectural Findings" in text
    assert "Recommendations" in text
    assert "Scope and Limitations" in text


# ============================================================
# Test 3: Verify internal dependencies are included
# ============================================================

def test_pdf_contains_actual_dependencies():
    report = sample_report()

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "module_a" in text
    assert "module_b" in text
    assert "Source Module" in text
    assert "Target Module" in text


# ============================================================
# Test 4: Verify architectural findings are included
# ============================================================

def test_pdf_contains_findings():
    report = sample_report()

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "CIRCULAR_DEPENDENCY" in text
    assert "Circular dependency detected" in text
    assert "module_a" in text
    assert "Architectural Findings" in text


# ============================================================
# Test 5: Verify rule-based recommendations
# ============================================================

def test_pdf_contains_rule_based_recommendations():
    report = sample_report()

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "Recommendations" in text
    assert "dependency cycle" in text
    assert "dependency inversion" in text


# ============================================================
# Test 6: Generate a report without findings
# ============================================================

def test_generate_report_without_findings():
    report = sample_report()

    report["findings"] = []
    report["summary"]["finding_count"] = 0

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "No architectural findings" in text
    assert "No rule-specific corrective actions" in text
    assert "Total Findings" in text


# ============================================================
# Test 7: Reject invalid report structures
# ============================================================

def test_reject_invalid_report_structure():
    generator = PDFReportGenerator()

    with pytest.raises(ValueError):
        generator.generate({
            "project_name": "Incomplete",
        })


# ============================================================
# Test 8: Safely render special characters
# ============================================================

def test_escaped_special_characters():
    report = sample_report()

    report["project_name"] = "Project <Alpha> & Beta"

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "Project <Alpha> & Beta" in text


# ============================================================
# Test 9: Verify extended architecture metrics
# ============================================================

def test_pdf_contains_extended_metrics():
    report = sample_report()

    # Add one class and one module-level function.
    report["modules"][0]["classes"] = [
        {
            "name": "Example",
            "methods": [],
            "bases": [],
        }
    ]

    report["modules"][0]["functions"] = ["main"]

    pdf = PDFReportGenerator().generate(report)
    text = extract_pdf_text(pdf)

    assert "Classes Detected" in text
    assert "Module-Level Functions" in text

    # Verify the report includes the expected metric values.
    assert "Python Modules" in text
    assert "Internal Dependencies" in text


# ============================================================
# Test 10: Keep small dependency tables together
# ============================================================

def test_small_dependency_table_stays_together():
    report = sample_report()

    report["dependencies"] = [
        {
            "source": f"package.source_{index}",
            "target": f"package.target_{index}",
        }
        for index in range(16)
    ]

    report["summary"]["dependency_count"] = 16

    pdf = PDFReportGenerator().generate(report)

    reader = PdfReader(BytesIO(pdf))

    pages = [
        page.extract_text() or ""
        for page in reader.pages
    ]

    # Both the first and final dependency rows should
    # appear on the same page.
    matching_pages = [
        page
        for page in pages
        if "package.source_0" in page
        and "package.source_15" in page
    ]

    assert len(matching_pages) == 1


# ============================================================
# Test 11: Preserve multipage PDF generation
# ============================================================

def test_report_preserves_multiple_page_output():
    report = sample_report()

    report["dependencies"] = [
        {
            "source": f"package.source_{index}",
            "target": f"package.target_{index}",
        }
        for index in range(80)
    ]

    report["summary"]["dependency_count"] = 80

    pdf = PDFReportGenerator().generate(report)

    reader = PdfReader(BytesIO(pdf))
    text = extract_pdf_text(pdf)

    assert len(reader.pages) > 1

    # Confirm the first and last dependencies are preserved.
    assert "package.source_0" in text
    assert "package.source_79" in text

    # Confirm subsequent report sections are not lost.
    assert "Architectural Findings" in text
    assert "Recommendations" in text
    assert "Scope and Limitations" in text
