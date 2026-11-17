
"""
ArchGuard AI — Interactive Software Architecture Dashboard.

Features:
    - FastAPI backend integration
    - Python project architecture analysis
    - Architecture summary metrics
    - Layer-aware dependency visualization
    - Architectural findings and severity filtering
    - Python module explorer
    - JSON and professional PDF report exports
    - Optional local Qwen AI architecture explanations

Architecture:
    Streamlit Dashboard -> FastAPI Backend
    FastAPI -> Application Services -> Domain Rules
    FastAPI -> Optional Ollama AI Adapter

The deterministic rule engine remains the authoritative
source of architectural findings.

AI explanations are optional and advisory.

The dashboard avoids st.dataframe() because some Windows
Application Control policies may block PyArrow DLLs.
"""

import json
import os
import re

import httpx
import streamlit as st

from archguard.adapters.pdf_report import PDFReportGenerator
from archguard.dashboard.visualization import (
    LAYER_ORDER,
    create_dependency_figure,
)


# ============================================================
# Configuration
# ============================================================

API_URL = os.getenv(
    "ARCHGUARD_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

st.set_page_config(
    page_title="ArchGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# FastAPI Backend Communication
# ============================================================

def check_api_health() -> bool:
    """Verify whether the FastAPI backend is available."""

    try:
        response = httpx.get(
            f"{API_URL}/health",
            timeout=5.0,
        )
        response.raise_for_status()

        return response.json().get("status") == "healthy"

    except (httpx.HTTPError, ValueError):
        return False


def analyze_project(project_path: str) -> dict:
    """Request deterministic architecture analysis from FastAPI."""

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{API_URL}/analyze",
            json={"project_path": project_path},
        )

        response.raise_for_status()
        return response.json()


def explain_project_architecture(project_path: str) -> dict:
    """
    Request Qwen explanations for verified findings.

    FastAPI independently analyzes the supplied project.
    The client cannot submit unverified findings.
    """

    with httpx.Client(timeout=180.0) as client:
        response = client.post(
            f"{API_URL}/analyze/explain",
            json={"project_path": project_path},
        )

        response.raise_for_status()
        return response.json()


# ============================================================
# Architecture Summary Metrics
# ============================================================

def display_summary(report: dict) -> None:
    """Display architectural metrics."""

    summary = report.get("summary", {})

    col1, col2, col3 = st.columns(3)

    col1.metric(
        label="Python Modules",
        value=summary.get("module_count", 0),
    )

    col2.metric(
        label="Internal Dependencies",
        value=summary.get("dependency_count", 0),
    )

    col3.metric(
        label="Architecture Findings",
        value=summary.get("finding_count", 0),
    )


# ============================================================
# Architectural Findings
# ============================================================

def display_findings(report: dict) -> None:
    """Display verified architectural findings."""

    findings = report.get("findings", [])

    if not findings:
        st.success(
            "No issues detected by the configured "
            "architecture rules."
        )

        st.caption(
            "This does not guarantee that the entire software "
            "architecture is free of design problems."
        )
        return

    severity_filter = st.multiselect(
        "Filter by severity",
        options=["error", "warning", "info"],
        default=["error", "warning", "info"],
    )

    filtered_findings = [
        finding
        for finding in findings
        if finding.get("severity") in severity_filter
    ]

    if not filtered_findings:
        st.info(
            "No architectural findings match "
            "the selected severity filters."
        )
        return

    for index, finding in enumerate(
        filtered_findings,
        start=1,
    ):
        severity = finding.get(
            "severity",
            "info",
        ).upper()

        rule_id = finding.get(
            "rule_id",
            "UNKNOWN_RULE",
        )

        with st.expander(
            f"{index}. {severity} — {rule_id}"
        ):
            st.write(
                "**Module:**",
                finding.get("module", "Unknown"),
            )
            st.write(
                "**Severity:**",
                severity,
            )
            st.write(
                "**Description:**",
                finding.get(
                    "message",
                    "No description available.",
                ),
            )


# ============================================================
# Python Module Explorer
# ============================================================

def display_modules(report: dict) -> None:
    """Explore classes, methods, functions, and imports."""

    modules = report.get("modules", [])

    if not modules:
        st.info("No Python modules were discovered.")
        return

    selected_name = st.selectbox(
        "Select a Python module",
        options=[
            module["name"]
            for module in modules
        ],
    )

    selected_module = next(
        module
        for module in modules
        if module["name"] == selected_name
    )

    st.write(
        "**File path:**",
        selected_module.get("path", ""),
    )

    # Imports
    st.subheader("Imports")

    imports = selected_module.get(
        "imports",
        [],
    )

    if imports:
        for imported in imports:
            st.code(
                imported,
                language="python",
            )
    else:
        st.info("No imports detected.")

    # Functions
    st.subheader("Functions")

    functions = selected_module.get(
        "functions",
        [],
    )

    if functions:
        for function in functions:
            st.code(
                function,
                language="python",
            )
    else:
        st.info(
            "No module-level functions detected."
        )

    # Classes
    st.subheader("Classes")

    classes = selected_module.get(
        "classes",
        [],
    )

    if not classes:
        st.info(
            "No classes detected in this module."
        )
        return

    for cls in classes:
        with st.expander(
            cls.get("name", "Unnamed Class")
        ):
            st.write(
                "**Class name:**",
                cls.get("name", ""),
            )

            st.write("**Methods:**")

            methods = cls.get(
                "methods",
                [],
            )

            if methods:
                for method in methods:
                    st.code(
                        method,
                        language="python",
                    )
            else:
                st.write(
                    "No methods detected."
                )

            st.write("**Base classes:**")

            bases = cls.get(
                "bases",
                [],
            )

            if bases:
                for base in bases:
                    st.code(
                        base,
                        language="python",
                    )
            else:
                st.write(
                    "No inheritance detected."
                )


# ============================================================
# Internal Dependency Listing
# ============================================================

def display_dependencies(report: dict) -> None:
    """
    Display internal dependencies without using st.dataframe().

    Avoids the PyArrow-related Windows Application
    Control issue encountered during development.
    """

    dependencies = report.get(
        "dependencies",
        [],
    )

    st.subheader("Internal Dependencies")

    if not dependencies:
        st.info(
            "No internal dependencies were detected."
        )
        return

    st.caption(
        f"{len(dependencies)} internal module "
        "dependencies identified."
    )

    for index, dependency in enumerate(
        dependencies,
        start=1,
    ):
        source = dependency.get(
            "source",
            "Unknown",
        )
        target = dependency.get(
            "target",
            "Unknown",
        )

        st.markdown(
            f"**{index}.** `{source}` → `{target}`"
        )


# ============================================================
# PDF and JSON Report Export
# ============================================================

def display_report_export(report: dict) -> None:
    """Export the architecture assessment as PDF or JSON."""

    st.subheader("Export Architecture Report")

    st.write(
        "Download the architecture assessment, including "
        "metrics, module dependencies, verified findings, "
        "and deterministic recommendations."
    )

    project_name = report.get(
        "project_name",
        "project",
    )

    safe_name = re.sub(
        r"[^A-Za-z0-9_-]",
        "_",
        project_name,
    ) or "project"

    report_json = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )

    try:
        pdf_bytes = PDFReportGenerator().generate(report)

    except (ValueError, OSError) as exc:
        pdf_bytes = None

        st.error(
            f"Unable to generate PDF report: {exc}"
        )

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="Download JSON Report",
            data=report_json,
            file_name=f"archguard_{safe_name}_report.json",
            mime="application/json",
            width="stretch",
        )

    with col2:
        if pdf_bytes is not None:
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name=f"archguard_{safe_name}_report.pdf",
                mime="application/pdf",
                width="stretch",
            )


# ============================================================
# AI Architecture Assistant
# ============================================================

def display_ai_assistant(
    report: dict,
    analyzed_project_path: str | None,
) -> None:
    """
    Display optional Qwen explanations.

    Verified findings remain separate from AI-generated
    suggestions. AI requests are initiated explicitly.
    """

    st.subheader("AI Architecture Assistant")

    st.caption(
        "Optional Qwen explanations generated locally through "
        "Ollama. Verified architectural findings come from "
        "ArchGuard's deterministic rule engine."
    )

    verified_findings = report.get(
        "findings",
        [],
    )

    st.write(
        "**Project:**",
        report.get("project_name", "Unknown"),
    )

    st.write(
        "**Verified architectural findings:**",
        len(verified_findings),
    )

    st.divider()

    # --------------------------------------------------------
    # Display verified findings
    # --------------------------------------------------------

    st.subheader("Verified Findings")

    if not verified_findings:
        st.success(
            "No architectural violations were detected "
            "by the currently configured rules."
        )

        st.info(
            "Qwen is not invoked when no findings exist. "
            "To test AI explanations, analyze a project "
            "with verified architectural violations."
        )

    else:
        st.warning(
            f"{len(verified_findings)} verified "
            "architectural finding(s) detected."
        )

        for index, finding in enumerate(
            verified_findings,
            start=1,
        ):
            with st.expander(
                f"{index}. "
                f"{finding.get('rule_id', 'UNKNOWN')}"
            ):
                st.write(
                    "**Severity:**",
                    finding.get(
                        "severity",
                        "unknown",
                    ),
                )

                st.write(
                    "**Module:**",
                    finding.get(
                        "module",
                        "Unknown",
                    ),
                )

                st.write(
                    "**Finding:**",
                    finding.get(
                        "message",
                        "",
                    ),
                )

    st.divider()

    # --------------------------------------------------------
    # AI explanation controls
    # --------------------------------------------------------

    st.subheader("Qwen Architecture Explanation")

    st.caption(
        "Qwen explains verified architecture findings, "
        "discusses possible consequences, and suggests "
        "refactoring strategies. Its output is advisory."
    )

    can_generate = (
        bool(verified_findings)
        and bool(analyzed_project_path)
        and len(verified_findings) <= 20
    )

    if len(verified_findings) > 20:
        st.warning(
            "The current AI adapter supports at most "
            "20 findings per request."
        )

    generate_clicked = st.button(
        "Generate AI Explanation",
        type="primary",
        disabled=not can_generate,
        width="stretch",
    )

    if generate_clicked:
        try:
            with st.spinner(
                "Qwen is generating an architecture explanation..."
            ):
                ai_result = explain_project_architecture(
                    analyzed_project_path
                )

            # Store the explanation together with the
            # backend's independently generated findings.
            st.session_state["ai_explanation"] = ai_result

        except httpx.HTTPStatusError as exc:
            st.session_state.pop(
                "ai_explanation",
                None,
            )

            if exc.response.status_code == 503:
                st.error(
                    "The local Ollama service is unavailable. "
                    "Verify that Ollama is running and the "
                    "configured Qwen model is installed."
                )
            else:
                st.error(
                    "AI explanation request failed. "
                    f"HTTP {exc.response.status_code}: "
                    f"{exc.response.text}"
                )

        except httpx.RequestError as exc:
            st.session_state.pop(
                "ai_explanation",
                None,
            )

            st.error(
                f"Unable to contact the FastAPI backend: {exc}"
            )

        except ValueError as exc:
            st.session_state.pop(
                "ai_explanation",
                None,
            )

            st.error(
                f"Invalid AI response: {exc}"
            )

    # --------------------------------------------------------
    # Display AI-generated explanation
    # --------------------------------------------------------

    ai_response = st.session_state.get(
        "ai_explanation"
    )

    if not ai_response:
        return

    ai = ai_response.get(
        "ai",
        {},
    )

    st.divider()

    st.subheader("AI-Generated Explanation")

    st.write(
        "**Model:**",
        ai.get("model", "Unknown"),
    )

    st.write(
        "**Status:**",
        ai.get("status", "Unknown"),
    )

    st.write(
        "**Findings explained:**",
        ai.get("finding_count", 0),
    )

    # The API re-analyzes the project when requesting
    # an explanation. Warn if the findings changed.
    if (
        ai_response.get("verified_findings", [])
        != verified_findings
    ):
        st.warning(
            "The findings changed between the original "
            "analysis and the AI request. Re-analyze the "
            "project to synchronize the results."
        )

    explanation = ai.get(
        "explanation",
        "No explanation returned.",
    )

    # Render untrusted AI output as plain text.
    st.text_area(
        "Qwen explanation",
        value=explanation,
        height=350,
        disabled=True,
    )

    st.caption(
        "AI explanations are advisory. Review all "
        "suggested refactoring changes before "
        "modifying source code."
    )


# ============================================================
# Main Dashboard
# ============================================================

def main() -> None:
    """Render the complete ArchGuard AI dashboard."""

    st.title("🛡️ ArchGuard AI")

    st.caption(
        "Intelligent Software Architecture Analysis System"
    )

    # --------------------------------------------------------
    # Sidebar: Backend connection
    # --------------------------------------------------------

    st.sidebar.header("Project Analysis")

    st.sidebar.caption(
        "Analyze a Python directory within "
        "the configured API workspace."
    )

    if check_api_health():
        st.sidebar.success("Backend connected")

    else:
        st.sidebar.error("Backend unavailable")

        st.warning(
            f"Start FastAPI on {API_URL} "
            "before analyzing a project."
        )

        st.stop()

    # --------------------------------------------------------
    # Sidebar: Project selection
    # --------------------------------------------------------

    project_path = st.sidebar.text_input(
        "Project directory",
        value="src",
        help=(
            "Enter a project directory inside "
            "the configured API workspace."
        ),
    )

    analyze_clicked = st.sidebar.button(
        "Analyze Project",
        type="primary",
        width="stretch",
    )

    # --------------------------------------------------------
    # Run deterministic architecture analysis
    # --------------------------------------------------------

    if analyze_clicked:
        if not project_path.strip():
            st.error(
                "Please enter a project directory."
            )

        else:
            try:
                with st.spinner(
                    "Analyzing software architecture..."
                ):
                    report = analyze_project(
                        project_path.strip()
                    )

                st.session_state["analysis_report"] = report

                # Preserve the exact analyzed path.
                st.session_state["analysis_project_path"] = (
                    project_path.strip()
                )

                # Invalidate previous AI explanations.
                st.session_state.pop(
                    "ai_explanation",
                    None,
                )

                st.success(
                    "Project analysis completed successfully."
                )

            except httpx.HTTPStatusError as exc:
                st.error(
                    "Architecture analysis failed. "
                    f"HTTP {exc.response.status_code}: "
                    f"{exc.response.text}"
                )

            except httpx.RequestError as exc:
                st.error(
                    f"Unable to contact FastAPI: {exc}"
                )

            except ValueError as exc:
                st.error(
                    f"Invalid backend response: {exc}"
                )

    # --------------------------------------------------------
    # Retrieve current architecture report
    # --------------------------------------------------------

    report = st.session_state.get(
        "analysis_report"
    )

    if report is None:
        st.info(
            "Select a project directory and click "
            "'Analyze Project' to begin."
        )
        return

    analyzed_project_path = st.session_state.get(
        "analysis_project_path"
    )

    st.divider()

    st.subheader(
        "Architecture Report: "
        f"{report.get('project_name', 'Unknown')}"
    )

    display_summary(report)

    st.divider()

    # --------------------------------------------------------
    # Dashboard tabs
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Dependency Graph",
            "Architectural Findings",
            "Module Explorer",
            "Export Report",
            "AI Architecture Assistant",
        ]
    )

    # --------------------------------------------------------
    # Tab 1: Architecture visualization
    # --------------------------------------------------------

    with tab1:
        st.subheader("Architecture Visualization")

        st.caption(
            "Explore module dependencies by architectural "
            "layer. Arrows point from importing modules "
            "toward their dependencies."
        )

        selected_layers = st.multiselect(
            "Visible architecture layers",
            options=list(LAYER_ORDER),
            default=list(LAYER_ORDER),
            help=(
                "Choose which architectural layers "
                "to display in the graph."
            ),
        )

        figure = create_dependency_figure(
            modules=report.get("modules", []),
            dependencies=report.get("dependencies", []),
            visible_layers=selected_layers,
        )

        st.plotly_chart(
            figure,
            width="stretch",
        )

        st.caption(
            "Hover over a node to view its complete module "
            "name, architectural layer, and dependency counts."
        )

        display_dependencies(report)

    # --------------------------------------------------------
    # Tab 2: Architectural findings
    # --------------------------------------------------------

    with tab2:
        display_findings(report)

    # --------------------------------------------------------
    # Tab 3: Module explorer
    # --------------------------------------------------------

    with tab3:
        display_modules(report)

    # --------------------------------------------------------
    # Tab 4: PDF and JSON exports
    # --------------------------------------------------------

    with tab4:
        display_report_export(report)

    # --------------------------------------------------------
    # Tab 5: AI Architecture Assistant
    # --------------------------------------------------------

    with tab5:
        display_ai_assistant(
            report=report,
            analyzed_project_path=analyzed_project_path,
        )


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":
    main()
