import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from backend.services.test_runner_factory import get_test_runner
from backend.services.test_runners.java_runner import JavaTestRunner


class JavaRunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.runner = JavaTestRunner()
        self.repo_path = Path("runtime") / "workspaces-test-java"

    @patch("backend.services.test_runners.base.run_shell_command")
    def test_install_dependencies_runs_maven_dependency_resolve(self, mock_run_shell_command):
        mock_run_shell_command.return_value = CompletedProcess(
            args="mvn dependency:resolve",
            returncode=0,
            stdout="dependencies resolved",
            stderr="",
        )

        result = self.runner.install_dependencies(
            repo_path=self.repo_path,
            install_config={"command": "mvn dependency:resolve"},
            project={"project_type": "java", "build_system": "maven"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["command"], "mvn dependency:resolve")
        self.assertEqual(result["step"], "install")

    @patch("backend.services.test_runners.base.run_shell_command")
    def test_run_tests_runs_maven_test(self, mock_run_shell_command):
        mock_run_shell_command.return_value = CompletedProcess(
            args="mvn test",
            returncode=0,
            stdout="tests passed",
            stderr="",
        )

        result = self.runner.run_tests(
            repo_path=self.repo_path,
            test_config={
                "command": "mvn test",
                "framework": "maven",
                "timeout_seconds": 600,
            },
            project={"project_type": "java", "build_system": "maven"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["command"], "mvn test")
        self.assertEqual(result["framework"], "maven")
        self.assertEqual(result["step"], "test")

    def test_factory_returns_java_runner(self):
        self.assertIsInstance(get_test_runner("java"), JavaTestRunner)


if __name__ == "__main__":
    unittest.main()
