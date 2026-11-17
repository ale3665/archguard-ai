
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class PythonClass:
    name: str
    methods: tuple[str, ...] = ()
    bases: tuple[str, ...] = ()


@dataclass(frozen=True)
class PythonModule:
    name: str
    path: str
    classes: tuple[PythonClass, ...] = ()
    functions: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dependency:
    source: str
    target: str


@dataclass(frozen=True)
class ArchitectureFinding:
    rule_id: str
    severity: Severity
    message: str
    module: str


@dataclass
class AnalysisReport:
    project_name: str
    modules: list[PythonModule] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    findings: list[ArchitectureFinding] = field(default_factory=list)

    @property
    def module_count(self) -> int:
        return len(self.modules)

    @property
    def finding_count(self) -> int:
        return len(self.findings)
