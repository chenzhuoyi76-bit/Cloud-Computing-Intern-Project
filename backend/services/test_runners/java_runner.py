from pathlib import Path
from typing import Any

from backend.services.test_runners.base import BaseTestRunner


class JavaTestRunner(BaseTestRunner):
    project_type = "java"

    def install_dependencies(
        self,
        repo_path: Path,
        install_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        return self._execute_step(
            step="install",
            command=install_config["command"],
            cwd=repo_path,
        )

    def run_tests(
        self,
        repo_path: Path,
        test_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        return self._execute_step(
            step="test",
            command=test_config["command"],
            cwd=repo_path,
            timeout_seconds=test_config["timeout_seconds"],
            extra_fields={"framework": test_config["framework"]},
        )
