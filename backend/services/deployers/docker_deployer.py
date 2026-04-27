import json
import subprocess
from time import perf_counter
from pathlib import Path
from typing import Any

from backend.services.deployers.base import BaseDeployer, DeploymentError


class DockerDeployer(BaseDeployer):
    target = "docker"

    def deploy(
        self,
        repo_path: Path,
        deploy_config: dict[str, Any],
        project: dict[str, Any],
    ) -> dict[str, Any]:
        deploy_started_at = perf_counter()
        docker_config = deploy_config["docker"]
        dockerfile_path = repo_path / docker_config["dockerfile_path"]
        if not dockerfile_path.exists():
            raise DeploymentError(f"Dockerfile not found: {docker_config['dockerfile_path']}")

        image_ref = f"{docker_config['image_name']}:{docker_config['image_tag']}"
        build_cmd = [
            "docker",
            "build",
            "-f",
            str(dockerfile_path),
            "-t",
            image_ref,
            ".",
        ]
        build_started_at = perf_counter()
        build_result = _run_command(build_cmd, cwd=repo_path)
        build_duration_seconds = round(perf_counter() - build_started_at, 3)
        if build_result.returncode != 0:
            raise DeploymentError(_format_failure("docker build", build_result))

        run_cmd = ["docker", "run", "-d", "--name", docker_config["container_name"]]
        for port in docker_config.get("ports", []):
            run_cmd.extend(["-p", _format_port_mapping(port)])
        for key, value in docker_config.get("env", {}).items():
            run_cmd.extend(["-e", f"{key}={value}"])
        run_cmd.append(image_ref)

        run_started_at = perf_counter()
        run_result = _run_command(run_cmd, cwd=repo_path)
        run_duration_seconds = round(perf_counter() - run_started_at, 3)
        if run_result.returncode != 0:
            raise DeploymentError(_format_failure("docker run", run_result))

        return {
            "step": "deploy",
            "target": "docker",
            "status": "passed",
            "duration_seconds": round(perf_counter() - deploy_started_at, 3),
            "build_duration_seconds": build_duration_seconds,
            "run_duration_seconds": run_duration_seconds,
            "image": image_ref,
            "container_name": docker_config["container_name"],
            "build_command": " ".join(build_cmd),
            "run_command": " ".join(run_cmd),
            "container_id": run_result.stdout.strip(),
            "build_stdout": build_result.stdout,
            "build_stderr": build_result.stderr,
            "run_stdout": run_result.stdout,
            "run_stderr": run_result.stderr,
        }

    def monitor_deployment(
        self,
        repo_path: Path,
        deploy_config: dict[str, Any],
        project: dict[str, Any],
        deploy_result: dict[str, Any],
        monitoring_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        monitoring_started_at = perf_counter()
        docker_config = deploy_config["docker"]
        container_ref = deploy_result.get("container_id") or docker_config["container_name"]
        inspect_cmd = [
            "docker",
            "inspect",
            "--format",
            "{{json .State}}",
            container_ref,
        ]
        inspect_result = _run_command(inspect_cmd, cwd=repo_path)
        duration_seconds = round(perf_counter() - monitoring_started_at, 3)
        if inspect_result.returncode != 0:
            raise DeploymentError(_format_failure("docker inspect", inspect_result))

        raw_state = (inspect_result.stdout or "").strip()
        try:
            state = json.loads(raw_state) if raw_state else {}
        except json.JSONDecodeError as exc:
            raise DeploymentError(f"docker inspect returned invalid state payload: {raw_state}") from exc

        running = bool(state.get("Running"))
        status = str(state.get("Status", "unknown"))

        return {
            "step": "monitor",
            "target": "docker",
            "status": "passed" if running else "failed",
            "duration_seconds": duration_seconds,
            "container_name": docker_config["container_name"],
            "container_id": deploy_result.get("container_id", ""),
            "container_status": status,
            "running": running,
            "inspect_command": " ".join(inspect_cmd),
            "inspect_stdout": inspect_result.stdout,
            "inspect_stderr": inspect_result.stderr,
        }


def _run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise DeploymentError("docker is not installed or not available in PATH.") from exc


def _format_port_mapping(port: Any) -> str:
    if isinstance(port, str):
        if not port.strip():
            raise DeploymentError("Docker port mapping cannot be empty.")
        return port.strip()

    if isinstance(port, dict):
        host = port.get("host")
        container = port.get("container")
        protocol = port.get("protocol")
        if host is None or container is None:
            raise DeploymentError("Docker port mapping object must include host and container.")

        mapping = f"{host}:{container}"
        if protocol:
            mapping = f"{mapping}/{protocol}"
        return mapping

    raise DeploymentError("Docker port mapping must be a string or an object.")


def _format_failure(step: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "Unknown docker error"
    return f"{step} failed: {detail}"
