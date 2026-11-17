
import json

import httpx
import networkx as nx
import plotly.graph_objects as go
import streamlit as st


API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="ArchGuard AI",
    page_icon="🛡️",
    layout="wide",
)


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
    """Request architecture analysis from FastAPI."""
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{API_URL}/analyze",
            json={"project_path": project_path},
        )

        response.raise_for_status()
        return response.json()


def create_dependency_figure(
    modules: list[dict],
    dependencies: list[dict],
) -> go.Figure:
    """Visualize project dependencies as a directed graph."""

    graph = nx.DiGraph()

    for module in modules:
        graph.add_node(module["name"])

    for dependency in dependencies:
        graph.add_edge(
            dependency["source"],
            dependency["target"],
        )

    figure = go.Figure()

    if not graph.nodes:
        figure.update_layout(
            title="No modules found",
            height=450,
        )
        return figure

    positions = nx.spring_layout(
        graph,
        seed=42,
    )

    # Draw dependencies as directed arrows.
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
            arrowwidth=1,
            arrowcolor="#64748b",
            opacity=0.65,
        )

    # Draw module nodes.
    node_x = []
    node_y = []
    node_labels = []
    node_sizes = []

    for node in graph.nodes():
        x, y = positions[node]

        node_x.append(x)
        node_y.append(y)
        node_labels.append(node)

        degree = graph.degree(node)
        node_sizes.append(18 + degree * 3)

    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_labels,
            textposition="top center",
            textfont=dict(size=10),
            hovertext=node_labels,
            hoverinfo="text",
            marker=dict(
                size=node_sizes,
                color="#2563eb",
                line=dict(
                    width=1,
                    color="#1e3a8a",
                ),
            ),
        )
    )

    figure.update_layout(
        title="Module Dependency Graph",
        showlegend=False,
        height=600,
        xaxis=dict(
            visible=False,
            range=[-1.5, 1.5],
        ),
        yaxis=dict(
            visible=False,
            range=[-1.5, 1.5],
            scaleanchor="x",
            scaleratio=1,
        ),
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return figure


def display_summary(report: dict) -> None:
    """Display architecture analysis metrics."""

    summary = report["summary"]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Python Modules",
        summary["module_count"],
    )

    col2.metric(
        "Internal Dependencies",
        summary["dependency_count"],
    )

    col3.metric(
        "Architecture Findings",
        summary["finding_count"],
    )


def display_findings(report: dict) -> None:
    """Display detected architectural issues."""

    findings = report["findings"]

    if not findings:
        st.success(
            "No issues detected by the configured "
            "architecture rules."
        )
        return

    severity_filter = st.multiselect(
        "Filter by severity",
        options=["error", "warning", "info"],
        default=["error", "warning", "info"],
    )

    filtered = [
        finding
        for finding in findings
        if finding["severity"] in severity_filter
    ]

    for finding in filtered:
        with st.expander(
            f"{finding['severity'].upper()} — "
            f"{finding['rule_id']}"
        ):
            st.write("**Module:**", finding["module"])
            st.write("**Description:**", finding["message"])


def display_modules(report: dict) -> None:
    """Display extracted module information."""

    modules = report["modules"]

    if not modules:
        st.info("No Python modules were discovered.")
        return

    selected = st.selectbox(
        "Select a module",
        options=[module["name"] for module in modules],
    )

    module = next(
        item for item in modules
        if item["name"] == selected
    )

    st.write("**File:**", module["path"])
    st.write("**Imports:**", module["imports"])
    st.write("**Functions:**", module["functions"])

    st.subheader("Classes")

    if module["classes"]:
        for cls in module["classes"]:
            with st.expander(cls["name"]):
                st.write("Methods:", cls["methods"])
                st.write("Base classes:", cls["bases"])
    else:
        st.info("No classes detected in this module.")


def main() -> None:
    """Render the ArchGuard AI dashboard."""

    st.title("🛡️ ArchGuard AI")
    st.caption(
        "Intelligent Software Architecture Analysis System"
    )

    st.sidebar.header("Project Analysis")
    st.sidebar.caption(
        "Analyze a Python directory within the "
        "configured API workspace."
    )

    if check_api_health():
        st.sidebar.success("Backend connected")
    else:
        st.sidebar.error("Backend unavailable")
        st.warning(
            "Start FastAPI on http://127.0.0.1:8000 "
            "before analyzing a project."
        )
        st.stop()

    project_path = st.sidebar.text_input(
        "Project directory",
        value="src",
        help="Example: src",
    )

    analyze_clicked = st.sidebar.button(
        "Analyze Project",
        type="primary",
        use_container_width=True,
    )

    if analyze_clicked:
        if not project_path.strip():
            st.error("Enter a project directory.")
        else:
            try:
                with st.spinner(
                    "Analyzing software architecture..."
                ):
                    report = analyze_project(
                        project_path.strip()
                    )

                st.session_state["analysis_report"] = report

            except httpx.HTTPStatusError as exc:
                st.error(
                    f"API returned HTTP "
                    f"{exc.response.status_code}: "
                    f"{exc.response.text}"
                )

            except httpx.RequestError as exc:
                st.error(
                    f"Unable to contact the API: {exc}"
                )

            except ValueError as exc:
                st.error(
                    f"Invalid API response: {exc}"
                )

    report = st.session_state.get("analysis_report")

    if report is None:
        st.info(
            "Select a project directory and click "
            "'Analyze Project' to begin."
        )
        return

    st.subheader(
        f"Architecture Report: {report['project_name']}"
    )

    display_summary(report)

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
            report["modules"],
            report["dependencies"],
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

        st.subheader("Internal Dependencies")

        st.dataframe(
            report["dependencies"],
            use_container_width=True,
        )

    with tab2:
        display_findings(report)

    with tab3:
        display_modules(report)

    with tab4:
        st.write(
            "Download the complete architecture analysis."
        )

        st.download_button(
            label="Download JSON Report",
            data=json.dumps(
                report,
                indent=2,
            ),
            file_name="archguard_report.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
