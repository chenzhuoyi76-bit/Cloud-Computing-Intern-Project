from __future__ import annotations

from pathlib import Path
from time import perf_counter, sleep
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from backend.services.deployers.base import BaseDeployer, DeploymentError, run_command


class AzureDeployer(BaseDeployer):
    target = "azure"

    def deploy(
        self,
        repo_path: Path,
        deploy_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        deploy_started_at = perf_counter()
        azure_config = deploy_config["azure"]
        command, shell = _resolve_azure_command(azure_config, repo_path)
        working_dir = _resolve_working_dir(repo_path, azure_config.get("working_dir", "."))

        run_result = run_command(command, cwd=working_dir, shell=shell)
        if run_result.returncode != 0:
            raise DeploymentError(_format_failure("azure deploy", run_result))

        return {
            "step": "deploy",
            "target": "azure",
            "status": "passed",
            "duration_seconds": round(perf_counter() - deploy_started_at, 3),
            "working_dir": str(working_dir),
            "deploy_mode": "command" if azure_config.get("command") else "template",
            "deploy_command": command if isinstance(command, str) else " ".join(command),
            "deployment_name": azure_config.get("deployment_name", ""),
            "resource_group": azure_config.get("resource_group", ""),
            "template_path": azure_config.get("template_path", ""),
            "stdout": run_result.stdout,
            "stderr": run_result.stderr,
            "returncode": run_result.returncode,
        }

    def monitor_deployment(
        self,
        repo_path: Path,
        deploy_config: dict[str, Any],
        project: dict[str, Any],
        deploy_result: dict[str, Any],
        monitoring_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        monitor_started_at = perf_counter()
        azure_config = deploy_config["azure"]
        healthcheck_url = str(azure_config.get("healthcheck_url", "")).strip()
        timeout_seconds = int(azure_config.get("healthcheck_timeout_seconds", 120))
        interval_seconds = float(azure_config.get("healthcheck_interval_seconds", 5))

        if not healthcheck_url:
            return {
                "step": "monitor",
                "target": "azure",
                "status": "passed",
                "duration_seconds": round(perf_counter() - monitor_started_at, 3),
                "probe_type": "none",
                "message": "未配置 Azure healthcheck_url，默认视为部署后监测通过。",
            }

        deadline = perf_counter() + timeout_seconds
        last_error = ""

        while perf_counter() < deadline:
            try:
                with urlopen(healthcheck_url, timeout=5) as response:
                    status_code = getattr(response, "status", None) or response.getcode()
                    body = response.read().decode("utf-8", errors="replace")
                    if 200 <= status_code < 300:
                        return {
                            "step": "monitor",
                            "target": "azure",
                            "status": "passed",
                            "duration_seconds": round(perf_counter() - monitor_started_at, 3),
                            "probe_type": "http",
                            "healthcheck_url": healthcheck_url,
                            "status_code": status_code,
                            "response_body": body,
                        }
                    last_error = f"HTTP {status_code}"
            except URLError as exc:
                last_error = str(exc.reason)
            except Exception as exc:  # pragma: no cover - defensive fallback
                last_error = str(exc)

            sleep(interval_seconds)

        return {
            "step": "monitor",
            "target": "azure",
            "status": "failed",
            "duration_seconds": round(perf_counter() - monitor_started_at, 3),
            "probe_type": "http",
            "healthcheck_url": healthcheck_url,
            "error": last_error or "Health check did not return a successful response before timeout.",
        }


def _resolve_azure_command(azure_config: dict[str, Any], repo_path: Path) -> tuple[list[str] | str, bool]:
    command = str(azure_config.get("command", "")).strip()
    if command:
        return command, True

    template_path = repo_path / str(azure_config.get("template_path", "")).strip()
    if not template_path.exists():
        raise DeploymentError(f"Azure deployment template not found: {azure_config.get('template_path', '')}")

    resource_group = str(azure_config.get("resource_group", "")).strip()
    deployment_name = str(azure_config.get("deployment_name", "")).strip()
    parameters_file = str(azure_config.get("parameters_file", "")).strip()
    subscription_id = str(azure_config.get("subscription_id", "")).strip()

    command_parts: list[str] = [
        "az",
        "deployment",
        "group",
        "create",
        "--name",
        deployment_name,
        "--resource-group",
        resource_group,
        "--template-file",
        str(template_path),
    ]

    if parameters_file:
        parameters_path = repo_path / parameters_file
        if not parameters_path.exists():
            raise DeploymentError(f"Azure deployment parameters file not found: {parameters_file}")
        command_parts.extend(["--parameters", f"@{parameters_path}"])

    if subscription_id:
        command_parts.extend(["--subscription", subscription_id])

    return command_parts, False


def _resolve_working_dir(repo_path: Path, working_dir: str) -> Path:
    resolved = (repo_path / working_dir).resolve()
    if not resolved.exists():
        raise DeploymentError(f"Azure working directory not found: {working_dir}")
    return resolved


def _format_failure(step: str, result: Any) -> str:
    detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "Unknown azure deploy error"
    return f"{step} failed: {detail}"
