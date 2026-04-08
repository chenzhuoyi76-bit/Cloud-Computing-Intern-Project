import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from backend.services.task_executor import execute_task_pipeline


class DummyRunner:
    def __init__(self, install_status="passed", test_status="passed"):
        self.install_status = install_status
        self.test_status = test_status

    def install_dependencies(self, repo_path, install_config, project):
        return {"status": self.install_status, "command": install_config["command"]}

    def run_tests(self, repo_path, test_config, project):
        return {"status": self.test_status, "command": test_config["command"]}


class DummyDeployer:
    def deploy(self, repo_path, deploy_config, project):
        return {"status": "passed", "target": "docker", "container_id": "abc123"}


class TaskExecutorTestCase(unittest.TestCase):
    def setUp(self):
        self.workspace_root = Path("runtime") / "workspaces-test-executor" / f"task_{uuid4().hex}"
        self.repo_path = self.workspace_root / "demo"
        self.repo_path.mkdir(parents=True, exist_ok=True)
        (self.repo_path / "Dockerfile").write_text("FROM python:3.13-slim\n", encoding="utf-8")
        self.task_request = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/demo.git",
                "project_type": "python",
            },
            "execution": {
                "install": {"enabled": True, "command": "pip install -r requirements.txt"},
                "test": {"enabled": True, "framework": "pytest", "command": "python -m pytest", "timeout_seconds": 600},
                "deploy": {"enabled": True, "target": "docker", "docker": {"dockerfile_path": "Dockerfile", "image_name": "demo", "image_tag": "latest", "container_name": "demo", "ports": [], "env": {}}},
            },
        }
        self.repository_result = {
            "workspace_path": str(self.workspace_root),
            "repo_path": str(self.repo_path),
            "repo_name": "demo",
            "repo_url": "https://github.com/example/demo.git",
            "branch": "main",
            "checked_out_ref": "main",
        }

    def tearDown(self):
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root, ignore_errors=True)

    @patch("backend.services.task_executor.get_deployer")
    @patch("backend.services.task_executor.get_test_runner")
    @patch("backend.services.task_executor.prepare_repository")
    def test_execute_pipeline_deploys_after_tests_pass(self, mock_prepare_repository, mock_get_test_runner, mock_get_deployer):
        mock_prepare_repository.return_value = self.repository_result
        mock_get_test_runner.return_value = DummyRunner()
        mock_get_deployer.return_value = DummyDeployer()

        result = execute_task_pipeline(self.task_request, workspace_root=str(self.workspace_root.parent))

        self.assertEqual(result["status"], "deployed")
        self.assertEqual(result["test_result"]["status"], "passed")
        self.assertEqual(result["deploy_result"]["status"], "passed")

    @patch("backend.services.task_executor.get_test_runner")
    @patch("backend.services.task_executor.prepare_repository")
    def test_execute_pipeline_does_not_deploy_when_tests_fail(self, mock_prepare_repository, mock_get_test_runner):
        mock_prepare_repository.return_value = self.repository_result
        mock_get_test_runner.return_value = DummyRunner(test_status="failed")

        result = execute_task_pipeline(self.task_request, workspace_root=str(self.workspace_root.parent))

        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["deploy_result"])
        self.assertEqual(result["dispatch_result"]["blocking_reason"], "unit_tests_not_passed")


if __name__ == "__main__":
    unittest.main()
