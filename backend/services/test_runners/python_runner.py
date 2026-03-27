import subprocess
from pathlib import Path
from typing import Any

from backend.services.test_runners.base import BaseTestRunner, TestExecutionError


class PythonTestRunner(BaseTestRunner):
    project_type = "python"

    def install_dependencies(
        self,
        repo_path: Path,
        install_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        command = install_config["command"]
        completed = _run_shell_command(command=command, cwd=repo_path)
        return {
            "step": "install",
            "status": "passed" if completed.returncode == 0 else "failed",
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def run_tests(
        self,
        repo_path: Path,
        test_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        command = test_config["command"]
        completed = _run_shell_command(
            command=command,
            cwd=repo_path,
            timeout_seconds=test_config["timeout_seconds"],
        )
        return {
            "step": "test",
            "status": "passed" if completed.returncode == 0 else "failed",
            "framework": test_config["framework"],
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }


def _run_shell_command(command: str, cwd: Path, timeout_seconds: int = 600) -> subprocess.CompletedProcess[str]:
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
