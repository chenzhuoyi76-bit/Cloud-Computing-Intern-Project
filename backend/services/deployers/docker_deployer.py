import subprocess
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
        build_result = _run_command(build_cmd, cwd=repo_path)
        if build_result.returncode != 0:
            raise DeploymentError(_format_failure("docker build", build_result))

        run_cmd = ["docker", "run", "-d", "--name", docker_config["container_name"]]
        for port in docker_config.get("ports", []):
            run_cmd.extend(["-p", port])
        for key, value in docker_config.get("env", {}).items():
            run_cmd.extend(["-e", f"{key}={value}"])
        run_cmd.append(image_ref)

        run_result = _run_command(run_cmd, cwd=repo_path)
        if run_result.returncode != 0:
            raise DeploymentError(_format_failure("docker run", run_result))

        return {
            "step": "deploy",
            "target": "docker",
            "status": "passed",
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


def _format_failure(step: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "Unknown docker error"
    return f"{step} failed: {detail}"
