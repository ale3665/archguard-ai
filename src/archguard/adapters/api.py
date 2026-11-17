
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from archguard.application.architecture_evaluator import (
    ArchitectureEvaluator,
)
from archguard.bootstrap import create_project_scanner


class AnalysisRequest(BaseModel):
    project_path: str = Field(min_length=1)


def create_app(
    allowed_root: str | Path = ".",
) -> FastAPI:
    """
    Create the ArchGuard API.

    Analysis is restricted to directories inside
    the configured workspace.
    """

    workspace = Path(allowed_root).resolve()

    app = FastAPI(
        title="ArchGuard AI",
        description="Software Architecture Analysis API",
        version="0.1.0",
    )

    @app.get("/health")
    def health():
        return {
            "status": "healthy",
            "application": "ArchGuard AI",
        }

    @app.post("/analyze")
    def analyze(request: AnalysisRequest):
        requested = Path(request.project_path)

        if requested.is_absolute():
            project_root = requested.resolve()
        else:
            project_root = (
                workspace / requested
            ).resolve()

        if not project_root.is_relative_to(workspace):
            raise HTTPException(
                status_code=403,
                detail="Project is outside the allowed workspace.",
            )

        if not project_root.is_dir():
            raise HTTPException(
                status_code=404,
                detail="Project directory not found.",
            )

        try:
            scanner = create_project_scanner()
            modules = scanner.scan(project_root)

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

        return {
            "project_name": report.project_name,
            "summary": {
                "module_count": report.module_count,
                "dependency_count": len(report.dependencies),
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


app = create_app()
