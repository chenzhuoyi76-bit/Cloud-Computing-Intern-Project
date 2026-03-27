from pathlib import Path
from typing import Any


class TestExecutionError(Exception):
    """Raised when the test execution step cannot be completed."""


class UnsupportedProjectTypeError(TestExecutionError):
    """Raised when no test runner is available for the given project type."""


class BaseTestRunner:
    project_type = ""

    def install_dependencies(
        self,
        repo_path: Path,
        install_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    def run_tests(
        self,
        repo_path: Path,
        test_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError
