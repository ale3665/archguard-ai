
from archguard.domain.models import (
    AnalysisReport,
    ArchitectureFinding,
    Dependency,
    PythonClass,
    PythonModule,
    Severity,
)


def test_python_class():
    cls = PythonClass(
        name="ProjectAnalyzer",
        methods=("analyze", "generate_report"),
        bases=("BaseAnalyzer",),
    )

    assert cls.name == "ProjectAnalyzer"
    assert "analyze" in cls.methods
    assert cls.bases == ("BaseAnalyzer",)


def test_python_module():
    module = PythonModule(
        name="analyzer",
        path="src/analyzer.py",
        imports=("ast", "pathlib"),
    )

    assert module.name == "analyzer"
    assert len(module.imports) == 2


def test_analysis_report():
    report = AnalysisReport(
        project_name="SampleProject",
        modules=[
            PythonModule(name="main", path="main.py"),
        ],
        dependencies=[
            Dependency(source="main", target="utils"),
        ],
        findings=[
            ArchitectureFinding(
                rule_id="CIRCULAR_DEPENDENCY",
                severity=Severity.WARNING,
                message="Circular dependency detected",
                module="main",
            ),
        ],
    )

    assert report.module_count == 1
    assert report.finding_count == 1
    assert len(report.dependencies) == 1
