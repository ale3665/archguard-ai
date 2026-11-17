
"""
ArchGuard AI — Interactive Software Architecture Dashboard.

Features:
    - FastAPI backend health monitoring
    - Python project architecture analysis
    - Architecture summary metrics
    - Interactive dependency graph
    - Architecture findings and severity filtering
    - Python module explorer
    - JSON report export

The dashboard communicates with the FastAPI backend
through HTTP requests.

The dependency listing intentionally avoids st.dataframe()
because certain Windows Application Control policies may
block native PyArrow DLLs.
"""

import json
import os

import httpx
import networkx as nx
import plotly.graph_objects as go
import streamlit as st


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
# Backend Communication
# ============================================================

def check_api_health() -> bool:
    """Check whether the FastAPI backend is available."""

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
    """
    Request project architecture analysis from FastAPI.

    Returns:
        Dictionary containing modules, dependencies,
        findings, and summary metrics.
    """

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{API_URL}/analyze",
            json={
                "project_path": project_path,
            },
        )

        response.raise_for_status()

        return response.json()


# ============================================================
# Dependency Graph Visualization
# ============================================================

def create_dependency_figure(
    modules: list[dict],
    dependencies: list[dict],
) -> go.Figure:
    """
    Create an interactive directed module dependency graph.

    Improvements:
        - Increased spacing between graph nodes
        - Short labels for better readability
        - Full module names displayed on hover
        - Directed edges
        - Node sizes based on connectivity
    """

    graph = nx.DiGraph()

    for module in modules:
        graph.add_node(module["name"])

    for dependency in dependencies:
        graph.add_edge(
            dependency["source"],
            dependency["target"],
        )

    figure = go.Figure()

    if graph.number_of_nodes() == 0:
        figure.update_layout(
            title="No Python modules discovered",
            height=450,
        )

        return figure

    # Calculate node positions using a reproducible layout.
    positions = nx.spring_layout(
        graph,
        seed=42,
        k=2.5,
        iterations=150,
    )

    # --------------------------------------------------------
    # Draw directed dependency arrows
    # --------------------------------------------------------

    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]

        figure.add_annotation(
            x=x1,
            y=y1,
            ax=x0,
            ay=y0,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.2,
            arrowcolor="#64748b",
            opacity=0.65,
        )

    # --------------------------------------------------------
    # Prepare module node information
    # --------------------------------------------------------

    node_x = []
    node_y = []

    node_labels = []
    node_hover_labels = []
    node_sizes = []

    for node in graph.nodes():
        x, y = positions[node]

        node_x.append(x)
        node_y.append(y)

        # Use the final module component as the short label.
        short_label = node.split(".")[-1]

        node_labels.append(short_label)

        # Preserve the fully qualified module name on hover.
        node_hover_labels.append(node)

        # Larger nodes represent more connected modules.
        degree = graph.degree(node)
        node_sizes.append(
            min(45, 18 + degree * 3)
        )

    # --------------------------------------------------------
    # Draw module nodes
    # --------------------------------------------------------

    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_labels,
            textposition="top center",
            textfont=dict(
                size=10,
                color="#334155",
            ),
            hovertext=node_hover_labels,
            hoverinfo="text",
            marker=dict(
                size=node_sizes,
                color="#2563eb",
                opacity=0.85,
                line=dict(
                    width=1,
                    color="#1e3a8a",
                ),
            ),
            name="Python Modules",
        )
    )

    figure.update_layout(
        title="Module Dependency Graph",
        showlegend=False,
        height=650,
        hovermode="closest",
        dragmode="pan",
        margin=dict(
            l=40,
            r=40,
            t=70,
            b=40,
        ),
        xaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    return figure


# ============================================================
# Architecture Summary
# ============================================================

def display_summary(report: dict) -> None:
    """Display key architecture analysis metrics."""

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
    """Display architectural findings with severity filtering."""

    findings = report.get("findings", [])

    if not findings:
        st.success(
            "No issues detected by the configured "
            "architecture rules."
        )

        st.caption(
            "This result does not guarantee that the entire "
            "software architecture is free of design problems."
        )

        return

    severity_filter = st.multiselect(
        "Filter by severity",
        options=[
            "error",
            "warning",
            "info",
        ],
        default=[
            "error",
            "warning",
            "info",
        ],
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
    """Display extracted classes, functions, and imports."""

    modules = report.get("modules", [])

    if not modules:
        st.info(
            "No Python modules were discovered."
        )

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

    # --------------------------------------------------------
    # Display imports
    # --------------------------------------------------------

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
        st.info(
            "No imports detected."
        )

    # --------------------------------------------------------
    # Display functions
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Display classes
    # --------------------------------------------------------

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

            st.write(
                "**Methods:**",
            )

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

            st.write(
                "**Base classes:**",
            )

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

    This avoids the PyArrow conversion path that may be
    blocked by Windows Application Control policies.
    """

    dependencies = report.get(
        "dependencies",
        [],
    )

    st.subheader(
        "Internal Dependencies"
    )

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
# JSON Report Export
# ============================================================

def display_report_export(report: dict) -> None:
    """Provide a downloadable JSON architecture report."""

    st.write(
        "Download the complete architecture analysis "
        "including modules, dependencies, and findings."
    )

    report_json = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )

    project_name = report.get(
        "project_name",
        "project",
    )

    # Use a safe filename for the downloaded report.
    safe_name = "".join(
        character
        if character.isalnum() or character in "-_"
        else "_"
        for character in project_name
    )

    st.download_button(
        label="Download JSON Report",
        data=report_json,
        file_name=f"archguard_{safe_name}_report.json",
        mime="application/json",
        use_container_width=True,
    )


# ============================================================
# Main Dashboard
# ============================================================

def main() -> None:
    """Render the complete ArchGuard AI dashboard."""

    st.title(
        "🛡️ ArchGuard AI"
    )

    st.caption(
        "Intelligent Software Architecture Analysis System"
    )

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    st.sidebar.header(
        "Project Analysis"
    )

    st.sidebar.caption(
        "Analyze a Python directory within "
        "the configured API workspace."
    )

    backend_available = check_api_health()

    if backend_available:
        st.sidebar.success(
            "Backend connected"
        )
    else:
        st.sidebar.error(
            "Backend unavailable"
        )

        st.warning(
            f"Start FastAPI on {API_URL} "
            "before analyzing a project."
        )

        st.stop()

    project_path = st.sidebar.text_input(
        "Project directory",
        value="src",
        help=(
            "Enter a relative directory within "
            "the API workspace, such as 'src'."
        ),
    )

    analyze_clicked = st.sidebar.button(
        "Analyze Project",
        type="primary",
        use_container_width=True,
    )

    # --------------------------------------------------------
    # Project analysis
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

                st.session_state[
                    "analysis_report"
                ] = report

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
                    f"Unable to connect to FastAPI: {exc}"
                )

            except ValueError as exc:
                st.error(
                    f"Invalid backend response: {exc}"
                )

    # --------------------------------------------------------
    # Display analysis results
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

    st.divider()

    st.subheader(
        f"Architecture Report: "
        f"{report.get('project_name', 'Unknown')}"
    )

    display_summary(report)

    st.divider()

    # --------------------------------------------------------
    # Dashboard tabs
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Dependency Graph",
            "Architectural Findings",
            "Module Explorer",
            "Export Report",
        ]
    )

    with tab1:
        figure = create_dependency_figure(
            report.get(
                "modules",
                [],
            ),
            report.get(
                "dependencies",
                [],
            ),
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

        display_dependencies(report)

    with tab2:
        display_findings(report)

    with tab3:
        display_modules(report)

    with tab4:
        display_report_export(report)


# ============================================================
# Application Entry Point
# ============================================================

if __name__ == "__main__":
    main()
