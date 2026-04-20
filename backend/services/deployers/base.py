from pathlib import Path
from typing import Any


class DeploymentError(Exception):
    """Raised when the deployment step cannot be completed."""


class UnsupportedDeployTargetError(DeploymentError):
    """Raised when no deployer is available for the given target."""


class BaseDeployer:
    target = ""

    def deploy(
        self,
        repo_path: Path,
        deploy_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    def monitor_deployment(
        self,
        repo_path: Path,
        deploy_config: dict[str, Any],
        project: dict[str, Any],
        deploy_result: dict[str, Any],
        monitoring_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError
