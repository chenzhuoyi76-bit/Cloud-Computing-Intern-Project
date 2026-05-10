import shutil
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import mkdtemp
from unittest.mock import MagicMock, patch

from backend.services.deployers.server_deployer import ServerDeployer


class ServerDeployerTestCase(unittest.TestCase):
    def setUp(self):
        self.repo_path = Path(mkdtemp(prefix="server-deployer-test-"))
        scripts_dir = self.repo_path / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "deploy.ps1").write_text("Write-Host 'deploy'", encoding="utf-8")
        self.deployer = ServerDeployer()
        self.deploy_config = {
            "server": {
                "script_path": "scripts/deploy.ps1",
                "start_command": "",
                "working_dir": ".",
                "healthcheck_url": "http://127.0.0.1:8080/health",
                "healthcheck_timeout_seconds": 10,
                "healthcheck_interval_seconds": 1,
            }
        }

    def tearDown(self):
        if self.repo_path.exists():
            shutil.rmtree(self.repo_path, ignore_errors=True)

    @patch("backend.services.deployers.server_deployer.run_command")
    def test_deploy_runs_server_script(self, mock_run_command):
        mock_run_command.return_value = CompletedProcess(
            args="scripts/deploy.ps1",
            returncode=0,
            stdout="deployed",
            stderr="",
        )

        result = self.deployer.deploy(
            repo_path=self.repo_path,
            deploy_config=self.deploy_config,
            project={"project_type": "python"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["target"], "server")
        self.assertEqual(result["deploy_mode"], "script")

    @patch("backend.services.deployers.server_deployer.urlopen")
    def test_monitor_deployment_passes_with_http_healthcheck(self, mock_urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.status = 200
        response.read.return_value = b'{"status":"ok"}'
        mock_urlopen.return_value = response

        result = self.deployer.monitor_deployment(
            repo_path=self.repo_path,
            deploy_config=self.deploy_config,
            project={"project_type": "python"},
            deploy_result={"status": "passed"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["probe_type"], "http")
        self.assertEqual(result["status_code"], 200)

    def test_monitor_deployment_passes_without_healthcheck(self):
        config = {
            "server": {
                "script_path": "scripts/deploy.ps1",
                "start_command": "",
                "working_dir": ".",
                "healthcheck_url": "",
                "healthcheck_timeout_seconds": 10,
                "healthcheck_interval_seconds": 1,
            }
        }

        result = self.deployer.monitor_deployment(
            repo_path=self.repo_path,
            deploy_config=config,
            project={"project_type": "python"},
            deploy_result={"status": "passed"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["probe_type"], "none")


if __name__ == "__main__":
    unittest.main()
