
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from archguard.application.architecture_evaluator import (
    ArchitectureEvaluator,
)
from archguard.bootstrap import create_project_scanner


# ============================================================
# Request Models
# ============================================================

class AnalysisRequest(BaseModel):
    """Request model for Python project architecture analysis."""

    project_path: str = Field(
        min_length=1,
        description=(
            "Path to a Python project directory within "
            "the configured workspace."
        ),
        examples=["src"],
    )


# ============================================================
# FastAPI Application Factory
# ============================================================

def create_app(
    allowed_root: str | Path = ".",
) -> FastAPI:
    """
    Create and configure the ArchGuard AI REST API.

    Features:
    - Application homepage
    - Health monitoring
    - Python project architecture analysis
    - Interactive OpenAPI documentation
    - Workspace boundary validation

    The analyzed project must be inside the allowed workspace.
    """

    workspace = Path(allowed_root).resolve()

    app = FastAPI(
        title="ArchGuard AI",
        description=(
            "An Intelligent Software Architecture Analysis System. "
            "Analyzes Python projects, extracts structural metadata, "
            "detects module dependencies, and evaluates architectural "
            "design rules."
        ),
        version="0.1.0",
    )

    # ========================================================
    # Homepage Endpoint
    # ========================================================

    @app.get(
        "/",
        tags=["Application"],
        summary="ArchGuard AI Homepage",
    )
    def home():
        """Return application information and available endpoints."""

        return {
            "application": "ArchGuard AI",
            "description": (
                "Intelligent Software Architecture Analysis System"
            ),
            "version": "0.1.0",
            "status": "running",
            "endpoints": {
                "home": "/",
                "health": "/health",
                "analyze": "/analyze",
                "documentation": "/docs",
                "openapi": "/openapi.json",
            },
        }

    # ========================================================
    # Health Check Endpoint
    # ========================================================

    @app.get(
        "/health",
        tags=["Application"],
        summary="Check API Health",
    )
    def health():
        """Check whether the ArchGuard API is operational."""

        return {
            "status": "healthy",
            "application": "ArchGuard AI",
        }

    # ========================================================
    # Architecture Analysis Endpoint
    # ========================================================

    @app.post(
        "/analyze",
        tags=["Architecture Analysis"],
        summary="Analyze a Python Project",
    )
    def analyze(request: AnalysisRequest):
        """
        Analyze a Python project's software architecture.

        The analysis includes:
        - Python modules and classes
        - Functions and imports
        - Internal module dependencies
        - Circular dependency detection
        - Coupling analysis
        - Architectural boundary violations

        Returns a structured JSON architecture report.
        """

        requested = Path(request.project_path)

        # Resolve the requested project location.
        if requested.is_absolute():
            project_root = requested.resolve()
        else:
            project_root = (
                workspace / requested
            ).resolve()

        # Restrict analysis to the configured workspace.
        if not project_root.is_relative_to(workspace):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Project is outside the allowed workspace."
                ),
            )

        # Verify that the requested directory exists.
        if not project_root.is_dir():
            raise HTTPException(
                status_code=404,
                detail="Project directory not found.",
            )

        try:
            # Assemble the scanner using dependency injection.
            scanner = create_project_scanner()

            # Extract Python modules from the project.
            modules = scanner.scan(project_root)

            # Evaluate architectural design rules.
            evaluator = ArchitectureEvaluator()

            report = evaluator.evaluate(
                project_name=project_root.name,
                modules=modules,
            )

        except (SyntaxError, UnicodeError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Unable to analyze project: {exc}",
            ) from exc

        except OSError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Unable to read project: {exc}",
            ) from exc

        # ====================================================
        # Structured Architecture Analysis Response
        # ====================================================

        return {
            "project_name": report.project_name,

            "summary": {
                "module_count": report.module_count,
                "dependency_count": len(
                    report.dependencies
                ),
                "finding_count": report.finding_count,
            },

            "modules": [
                {
                    "name": module.name,
                    "path": module.path,

                    "classes": [
                        {
                            "name": cls.name,
                            "methods": list(cls.methods),
                            "bases": list(cls.bases),
                        }
                        for cls in module.classes
                    ],

                    "functions": list(module.functions),
                    "imports": list(module.imports),
                }
                for module in report.modules
            ],

            "dependencies": [
                {
                    "source": dependency.source,
                    "target": dependency.target,
                }
                for dependency in report.dependencies
            ],

            "findings": [
                {
                    "rule_id": finding.rule_id,
                    "severity": finding.severity.value,
                    "message": finding.message,
                    "module": finding.module,
                }
                for finding in report.findings
            ],
        }

    return app


# ============================================================
# Application Entry Point
# ============================================================

app = create_app()
