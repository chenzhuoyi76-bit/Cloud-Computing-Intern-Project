import subprocess
from time import perf_counter
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

    def _execute_step(
        self,
        *,
        step: str,
        command: str,
        cwd: Path,
        timeout_seconds: int = 600,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        completed = run_shell_command(
            command=command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        result = {
            "step": step,
            "status": "passed" if completed.returncode == 0 else "failed",
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_seconds": round(perf_counter() - started_at, 3),
        }
        if extra_fields:
            result.update(extra_fields)
        return result


def run_shell_command(
    command: str,
    cwd: Path,
    timeout_seconds: int = 600,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise TestExecutionError("Required command is not available in PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise TestExecutionError(f"Command timed out after {timeout_seconds} seconds: {command}") from exc
