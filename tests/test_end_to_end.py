
"""
ArchGuard AI — End-to-End Integration Tests.

Verifies the complete workflow:
Python project -> FastAPI -> architecture analysis -> PDF.

The test projects are generated in temporary directories.
No real user source files are modified.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from archguard.adapters.api import create_app
from archguard.adapters.pdf_report import PDFReportGenerator


@pytest.fixture
def sample_project(tmp_path):
    """Create a project with known architectural violations."""

    root = tmp_path / "sample_project"
    root.mkdir()

    # --------------------------------------------------------
    # Create a circular module dependency
    # --------------------------------------------------------

    (root / "a.py").write_text(
        "import b\n",
        encoding="utf-8",
    )

    (root / "b.py").write_text(
        "import a\n",
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Create a forbidden Hexagonal Architecture dependency
    # --------------------------------------------------------

    package = root / "archguard"
    domain = package / "domain"
    adapters = package / "adapters"

    domain.mkdir(parents=True)
    adapters.mkdir(parents=True)

    for initializer in (
        package / "__init__.py",
        domain / "__init__.py",
        adapters / "__init__.py",
    ):
        initializer.write_text(
            "",
            encoding="utf-8",
        )

    # Domain must not depend directly on adapters.
    (domain / "models.py").write_text(
        "import archguard.adapters.storage\n",
        encoding="utf-8",
    )

    (adapters / "storage.py").write_text(
        "class Storage:\n"
        "    pass\n",
        encoding="utf-8",
    )

    return root


@pytest.fixture
def analysis_response(sample_project):
    """Analyze the temporary project through FastAPI."""

    client = TestClient(
        create_app(sample_project.parent)
    )

    response = client.post(
        "/analyze",
        json={
            "project_path": sample_project.name,
        },
    )

    assert response.status_code == 200

    return response.json()


# ============================================================
# PDF Text Extraction
# ============================================================

def pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract and normalize text from every PDF page.

    Whitespace normalization prevents false test failures
    caused by line breaks inserted by PDF text extraction.
    """

    reader = PdfReader(BytesIO(pdf_bytes))

    combined = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    return " ".join(combined.split())


# ============================================================
# Test 1: Complete architecture analysis
# ============================================================

def test_end_to_end_architecture_analysis(analysis_response):
    report = analysis_response

    assert report["project_name"] == "sample_project"

    rule_ids = {
        finding["rule_id"]
        for finding in report["findings"]
    }

    assert "CIRCULAR_DEPENDENCY" in rule_ids
    assert "LAYER_BOUNDARY_VIOLATION" in rule_ids

    assert report["summary"]["finding_count"] >= 2


# ============================================================
# Test 2: Export detected problems into PDF
# ============================================================

def test_end_to_end_pdf_contains_findings(analysis_response):
    pdf = PDFReportGenerator().generate(
        analysis_response
    )

    assert pdf.startswith(b"%PDF-")

    text = pdf_text(pdf)

    assert "sample_project" in text
    assert "CIRCULAR_DEPENDENCY" in text
    assert "LAYER_BOUNDARY_VIOLATION" in text


# ============================================================
# Test 3: PDF summary matches the API analysis
# ============================================================

def test_pdf_metrics_match_api_results(analysis_response):
    report = analysis_response

    module_count = len(report["modules"])
    dependency_count = len(report["dependencies"])
    finding_count = len(report["findings"])

    assert report["summary"]["module_count"] == module_count
    assert report["summary"]["dependency_count"] == dependency_count
    assert report["summary"]["finding_count"] == finding_count

    pdf = PDFReportGenerator().generate(report)
    text = pdf_text(pdf)

    assert f"analyzed {module_count} Python modules" in text
    assert f"identified {dependency_count} internal module" in text
    assert f"produced {finding_count} findings" in text


# ============================================================
# Test 4: PDF includes relevant recommendations
# ============================================================

def test_pdf_recommendations_match_findings(analysis_response):
    pdf = PDFReportGenerator().generate(
        analysis_response
    )

    text = pdf_text(pdf)

    assert "Recommendations" in text
    assert "dependency cycle" in text
    assert "forbidden cross-layer dependency" in text


# ============================================================
# Test 5: Large reports support multiple pages
# ============================================================

def test_large_pdf_report_pagination():
    """
    Verify report generation with many dependencies.

    Ensures that multi-page PDFs retain content from
    both the beginning and end of dependency listings.
    """

    dependencies = [
        {
            "source": f"package.source_{index}",
            "target": f"package.target_{index}",
        }
        for index in range(80)
    ]

    report = {
        "project_name": "LargeProject",
        "summary": {
            "module_count": 160,
            "dependency_count": 80,
            "finding_count": 0,
        },
        "modules": [
            {
                "name": f"module_{index}",
            }
            for index in range(160)
        ],
        "dependencies": dependencies,
        "findings": [],
    }

    pdf = PDFReportGenerator().generate(report)

    reader = PdfReader(BytesIO(pdf))

    assert len(reader.pages) > 1

    text = pdf_text(pdf)

    assert "LargeProject" in text
    assert "package.source_0" in text
    assert "package.source_79" in text
    assert "Scope and Limitations" in text
