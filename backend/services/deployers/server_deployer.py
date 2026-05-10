from __future__ import annotations

from pathlib import Path
from time import perf_counter, sleep
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from backend.services.deployers.base import BaseDeployer, DeploymentError, run_command


class ServerDeployer(BaseDeployer):
    target = "server"

    def deploy(
        self,
        repo_path: Path,
        deploy_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        deploy_started_at = perf_counter()
        server_config = deploy_config["server"]
        command, shell = _resolve_server_command(server_config, repo_path)
        working_dir = _resolve_working_dir(repo_path, server_config.get("working_dir", "."))

        run_result = run_command(command, cwd=working_dir, shell=shell)
        if run_result.returncode != 0:
            raise DeploymentError(_format_failure("server deploy", run_result))

        return {
            "step": "deploy",
            "target": "server",
            "status": "passed",
            "duration_seconds": round(perf_counter() - deploy_started_at, 3),
            "working_dir": str(working_dir),
            "deploy_mode": "script" if server_config.get("script_path") else "command",
            "deploy_command": command if isinstance(command, str) else " ".join(command),
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
        server_config = deploy_config["server"]
        healthcheck_url = str(server_config.get("healthcheck_url", "")).strip()
        timeout_seconds = int(server_config.get("healthcheck_timeout_seconds", 60))
        interval_seconds = float(server_config.get("healthcheck_interval_seconds", 2))

        if not healthcheck_url:
            return {
                "step": "monitor",
                "target": "server",
                "status": "passed",
                "duration_seconds": round(perf_counter() - monitor_started_at, 3),
                "probe_type": "none",
                "message": "未配置 server healthcheck_url，默认视为部署后监测通过。",
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
                            "target": "server",
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
            "target": "server",
            "status": "failed",
            "duration_seconds": round(perf_counter() - monitor_started_at, 3),
            "probe_type": "http",
            "healthcheck_url": healthcheck_url,
            "error": last_error or "Health check did not return a successful response before timeout.",
        }


def _resolve_server_command(server_config: dict[str, Any], repo_path: Path) -> tuple[list[str] | str, bool]:
    script_path = str(server_config.get("script_path", "")).strip()
    start_command = str(server_config.get("start_command", "")).strip()

    if script_path:
        resolved_script = repo_path / script_path
        if not resolved_script.exists():
            raise DeploymentError(f"Server deploy script not found: {script_path}")
        script_suffix = resolved_script.suffix.lower()
        if script_suffix == ".ps1":
            return [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(resolved_script),
            ], False
        if script_suffix in {".cmd", ".bat"}:
            return ["cmd", "/c", str(resolved_script)], False
        return str(resolved_script), True

    if start_command:
        return start_command, True

    raise DeploymentError("Server deployment requires either server.script_path or server.start_command.")


def _resolve_working_dir(repo_path: Path, working_dir: str) -> Path:
    resolved = (repo_path / working_dir).resolve()
    if not resolved.exists():
        raise DeploymentError(f"Server working directory not found: {working_dir}")
    return resolved


def _format_failure(step: str, result: Any) -> str:
    detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "Unknown server deploy error"
    return f"{step} failed: {detail}"
