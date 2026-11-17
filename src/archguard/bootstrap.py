
from archguard.adapters.ast_parser import ASTSourceCodeParser
from archguard.application.project_scanner import ProjectScanner


def create_project_scanner() -> ProjectScanner:
    """Assemble the scanner with its concrete parser adapter."""

    parser = ASTSourceCodeParser()

    return ProjectScanner(parser=parser)
