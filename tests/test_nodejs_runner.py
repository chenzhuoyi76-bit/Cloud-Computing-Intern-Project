import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from backend.services.test_runners.nodejs_runner import NodejsTestRunner


class NodejsRunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.runner = NodejsTestRunner()
        self.repo_path = Path("runtime") / "workspaces-test-nodejs"

    @patch("backend.services.test_runners.base.run_shell_command")
    def test_install_dependencies_runs_npm_install(self, mock_run_shell_command):
        mock_run_shell_command.return_value = CompletedProcess(
            args="npm install",
            returncode=0,
            stdout="installed",
            stderr="",
        )

        result = self.runner.install_dependencies(
            repo_path=self.repo_path,
            install_config={"command": "npm install"},
            project={"project_type": "nodejs"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["command"], "npm install")
        self.assertEqual(result["step"], "install")

    @patch("backend.services.test_runners.base.run_shell_command")
    def test_run_tests_runs_npm_test(self, mock_run_shell_command):
        mock_run_shell_command.return_value = CompletedProcess(
            args="npm test",
            returncode=0,
            stdout="tests passed",
            stderr="",
        )

        result = self.runner.run_tests(
            repo_path=self.repo_path,
            test_config={
                "command": "npm test",
                "framework": "npm",
                "timeout_seconds": 600,
            },
            project={"project_type": "nodejs"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["command"], "npm test")
        self.assertEqual(result["framework"], "npm")
        self.assertEqual(result["step"], "test")


if __name__ == "__main__":
    unittest.main()
