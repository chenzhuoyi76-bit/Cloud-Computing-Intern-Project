import shutil
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import mkdtemp
from unittest.mock import MagicMock, patch

from backend.services.deployers.azure_deployer import AzureDeployer


class AzureDeployerTestCase(unittest.TestCase):
    def setUp(self):
        self.repo_path = Path(mkdtemp(prefix="azure-deployer-test-"))
        infra_dir = self.repo_path / "infra"
        infra_dir.mkdir(parents=True, exist_ok=True)
        (infra_dir / "main.bicep").write_text("targetScope = 'resourceGroup'", encoding="utf-8")
        (infra_dir / "main.parameters.json").write_text("{}", encoding="utf-8")
        self.deployer = AzureDeployer()
        self.deploy_config = {
            "azure": {
                "command": "",
                "template_path": "infra/main.bicep",
                "parameters_file": "infra/main.parameters.json",
                "resource_group": "demo-rg",
                "deployment_name": "demo-deployment",
                "subscription_id": "sub-123",
                "working_dir": ".",
                "healthcheck_url": "https://demo.example.com/health",
                "healthcheck_timeout_seconds": 30,
                "healthcheck_interval_seconds": 1,
            }
        }

    def tearDown(self):
        if self.repo_path.exists():
            shutil.rmtree(self.repo_path, ignore_errors=True)

    @patch("backend.services.deployers.azure_deployer.run_command")
    def test_deploy_builds_group_command_from_template(self, mock_run_command):
        mock_run_command.return_value = CompletedProcess(
            args="az deployment group create",
            returncode=0,
            stdout='{"properties":{"provisioningState":"Succeeded"}}',
            stderr="",
        )

        result = self.deployer.deploy(
            repo_path=self.repo_path,
            deploy_config=self.deploy_config,
            project={"project_type": "python"},
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["target"], "azure")
        self.assertEqual(result["deploy_mode"], "template")
        command = mock_run_command.call_args.args[0]
        self.assertIn("az", command)
        self.assertIn("--resource-group", command)
        self.assertIn("demo-rg", command)

    @patch("backend.services.deployers.azure_deployer.urlopen")
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
            "azure": {
                "command": "az deployment group create --resource-group demo-rg --template-file infra/main.bicep",
                "template_path": "",
                "parameters_file": "",
                "resource_group": "",
                "deployment_name": "demo-deployment",
                "subscription_id": "",
                "working_dir": ".",
                "healthcheck_url": "",
                "healthcheck_timeout_seconds": 30,
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
