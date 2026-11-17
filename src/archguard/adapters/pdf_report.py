
"""
ArchGuard AI — PDF Architecture Report Generator.

Generates professional architecture assessment reports
from verified analysis results returned by the API.

No AI-generated findings or invented metrics are used.
"""

from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


RECOMMENDATIONS = {
    "CIRCULAR_DEPENDENCY": (
        "Review the dependency cycle and consider separating "
        "shared responsibilities into independent modules. "
        "Use interfaces or dependency inversion where appropriate."
    ),
    "HIGH_COUPLING": (
        "Review the module's responsibilities and direct "
        "dependencies. Consider separating unrelated concerns "
        "and introducing focused abstractions."
    ),
    "LAYER_BOUNDARY_VIOLATION": (
        "Remove the forbidden cross-layer dependency. "
        "Introduce an application-level port or interface "
        "and connect its implementation through dependency injection."
    ),
}


def _safe(value: object) -> str:
    """Escape text for ReportLab paragraphs."""
    return escape(str(value))


class PDFReportGenerator:
    """Generate PDF documents from ArchGuard analysis reports."""

    def __init__(self):
        styles = getSampleStyleSheet()

        self.styles = {
            "title": ParagraphStyle(
                "ArchGuardTitle",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=19,
                leading=24,
                textColor=colors.black,
                alignment=TA_LEFT,
                spaceAfter=8,
            ),
            "subtitle": ParagraphStyle(
                "ArchGuardSubtitle",
                parent=styles["Normal"],
                fontSize=10,
                leading=15,
                textColor=colors.black,
                spaceAfter=12,
            ),
            "heading": ParagraphStyle(
                "ArchGuardHeading",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=16,
                textColor=colors.black,
                spaceBefore=14,
                spaceAfter=7,
            ),
            "body": ParagraphStyle(
                "ArchGuardBody",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                textColor=colors.black,
                spaceAfter=7,
            ),
            "small": ParagraphStyle(
                "ArchGuardSmall",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                textColor=colors.black,
                spaceAfter=4,
            ),
            "table": ParagraphStyle(
                "ArchGuardTable",
                parent=styles["Normal"],
                fontSize=8,
                leading=11,
                textColor=colors.black,
            ),
            "table_header": ParagraphStyle(
                "ArchGuardTableHeader",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=11,
                textColor=colors.black,
            ),
        }

    def _p(self, value: object, style: str = "body") -> Paragraph:
        return Paragraph(
            _safe(value),
            self.styles[style],
        )

    def _heading(self, title: str) -> Paragraph:
        return self._p(title, "heading")

    def _table(self, headings: list[str], rows: list[list]) -> Table:
        data = [
            [
                self._p(heading, "table_header")
                for heading in headings
            ]
        ]

        for row in rows:
            data.append([
                self._p(value, "table")
                for value in row
            ])

        table = Table(
            data,
            colWidths=[
                (7.3 * inch) / len(headings)
                for _ in headings
            ],
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )

        return table

    @staticmethod
    def _footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.black)
        canvas.drawString(
            0.6 * inch,
            0.4 * inch,
            "ArchGuard AI | Automated Architecture Assessment",
        )
        canvas.drawRightString(
            7.9 * inch,
            0.4 * inch,
            f"Page {document.page}",
        )
        canvas.restoreState()

    def _recommendations(self, findings: list[dict]) -> list[str]:
        """Return deterministic recommendations for detected rule IDs."""

        rule_ids = sorted({
            finding.get("rule_id", "")
            for finding in findings
        })

        return [
            RECOMMENDATIONS[rule_id]
            for rule_id in rule_ids
            if rule_id in RECOMMENDATIONS
        ]

    def generate(self, report: dict) -> bytes:
        """
        Generate a PDF report from an analysis response.

        Returns:
            Raw PDF bytes suitable for downloading.

        Raises:
            ValueError: If essential report fields are missing.
        """

        required = {
            "project_name",
            "summary",
            "modules",
            "dependencies",
            "findings",
        }

        if not isinstance(report, dict) or not required.issubset(report):
            raise ValueError("Invalid architecture report structure.")

        summary = report["summary"]
        modules = report["modules"]
        dependencies = report["dependencies"]
        findings = report["findings"]

        if not (
            isinstance(summary, dict)
            and isinstance(modules, list)
            and isinstance(dependencies, list)
            and isinstance(findings, list)
        ):
            raise ValueError("Invalid report data types.")

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.6 * inch,
            leftMargin=0.6 * inch,
            topMargin=0.65 * inch,
            bottomMargin=0.7 * inch,
            title="ArchGuard AI Architecture Assessment",
            author="ArchGuard AI",
        )

        story = []

        # ----------------------------------------------------
        # Title and metadata
        # ----------------------------------------------------

        story.append(self._p(
            "ArchGuard AI",
            "title",
        ))

        story.append(self._p(
            "Software Architecture Assessment Report",
            "subtitle",
        ))

        story.append(self._p(
            f"Project: {report['project_name']}",
        ))

        generated_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )

        story.append(self._p(
            f"Generated: {generated_at}",
            "small",
        ))

        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.black,
        ))

        # ----------------------------------------------------
        # Executive summary
        # ----------------------------------------------------

        story.append(self._heading("1. Executive Summary"))

        module_count = len(modules)
        dependency_count = len(dependencies)
        finding_count = len(findings)

        story.append(self._p(
            f"ArchGuard AI analyzed {module_count} Python modules "
            f"and identified {dependency_count} internal module "
            f"dependencies. The configured architecture rules "
            f"produced {finding_count} findings."
        ))

        # ----------------------------------------------------
        # Architecture metrics
        # ----------------------------------------------------

        story.append(self._heading("2. Architecture Metrics"))

        severity_counts = Counter(
            finding.get("severity", "unknown")
            for finding in findings
        )

        metrics = [
            ["Python Modules", module_count],
            ["Internal Dependencies", dependency_count],
            ["Total Findings", finding_count],
            ["Error Findings", severity_counts.get("error", 0)],
            ["Warning Findings", severity_counts.get("warning", 0)],
            ["Informational Findings", severity_counts.get("info", 0)],
        ]

        story.append(self._table(
            ["Metric", "Value"],
            metrics,
        ))

        # ----------------------------------------------------
        # Internal module dependencies
        # ----------------------------------------------------

        story.append(self._heading("3. Module Dependencies"))

        if dependencies:
            rows = [
                [
                    item.get("source", ""),
                    item.get("target", ""),
                ]
                for item in dependencies
            ]

            story.append(self._table(
                ["Source Module", "Target Module"],
                rows,
            ))
        else:
            story.append(self._p(
                "No internal module dependencies were identified."
            ))

        # ----------------------------------------------------
        # Architectural findings
        # ----------------------------------------------------

        story.append(self._heading("4. Architectural Findings"))

        if findings:
            for index, finding in enumerate(findings, start=1):
                story.append(KeepTogether([
                    self._p(
                        f"{index}. {finding.get('rule_id', 'UNKNOWN')} "
                        f"({finding.get('severity', 'unknown').upper()})",
                        "small",
                    ),
                    self._p(
                        f"Module: {finding.get('module', 'Unknown')}",
                        "small",
                    ),
                    self._p(
                        finding.get("message", ""),
                        "body",
                    ),
                    Spacer(1, 4),
                ]))
        else:
            story.append(self._p(
                "No architectural findings were produced by "
                "the currently configured rules."
            ))

        # ----------------------------------------------------
        # Recommendations
        # ----------------------------------------------------

        story.append(self._heading("5. Recommendations"))

        recommendations = self._recommendations(findings)

        if recommendations:
            for index, recommendation in enumerate(
                recommendations,
                start=1,
            ):
                story.append(self._p(
                    f"{index}. {recommendation}"
                ))
        else:
            story.append(self._p(
                "No rule-specific corrective actions are required "
                "based on the findings produced in this analysis. "
                "Continue reviewing module responsibilities, "
                "test coverage, and architecture boundaries."
            ))

        # ----------------------------------------------------
        # Scope and limitations
        # ----------------------------------------------------

        story.append(self._heading("6. Scope and Limitations"))

        story.append(self._p(
            "This assessment uses static analysis of Python "
            "source files. It evaluates selected architectural "
            "rules, including circular module dependencies, "
            "direct internal coupling thresholds, and configured "
            "layer boundaries. Results do not guarantee that "
            "the entire software architecture is correct."
        ))

        story.append(self._p(
            "Dynamic imports, runtime behavior, and unsupported "
            "import patterns may not be fully represented. "
            "Recommendations are rule-based and should be "
            "reviewed by a software engineer before implementation.",
            "small",
        ))

        document.build(
            story,
            onFirstPage=self._footer,
            onLaterPages=self._footer,
        )

        return buffer.getvalue()
