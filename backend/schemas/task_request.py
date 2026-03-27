from copy import deepcopy
from typing import Any
from urllib.parse import urlparse


SUPPORTED_INTENTS = {
    "run_test",
    "deploy_project",
    "package_project",
    "merge_code",
    "check_service_status",
    "summarize_monitoring",
}
SUPPORTED_PROJECT_TYPES = {"python", "nodejs", "java"}
SUPPORTED_DEPLOY_TARGETS = {"docker", "server", "cloud"}


class TaskRequestValidationError(Exception):
    """Raised when the task request payload is invalid."""


def validate_task_request(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TaskRequestValidationError("Task request must be a JSON object.")

    data = deepcopy(payload)
    intent = _require_non_empty_string(data, "intent")
    if intent not in SUPPORTED_INTENTS:
        raise TaskRequestValidationError(f"Unsupported intent: {intent}")

    project = _require_object(data, "project")
    repo_url = _require_non_empty_string(project, "repo_url", prefix="project")
    _validate_repo_url(repo_url)

    project_type = _require_non_empty_string(project, "project_type", prefix="project")
    if project_type not in SUPPORTED_PROJECT_TYPES:
        raise TaskRequestValidationError(f"Unsupported project.project_type: {project_type}")

    project.setdefault("branch", "main")
    project.setdefault("commit_sha", "")
    project.setdefault("root_path", ".")
    project.setdefault("language_version", "")
    project.setdefault("build_system", _default_build_system(project_type))

    quality_gate = _optional_object(data, "quality_gate", prefix="quality_gate")
    quality_gate.setdefault("unit_tests_required", True)
    quality_gate.setdefault("unit_tests_passed", False)
    quality_gate.setdefault("block_on_test_failure", True)
    quality_gate.setdefault("block_on_missing_tests", True)
    _validate_bool_fields(
        quality_gate,
        [
            "unit_tests_required",
            "unit_tests_passed",
            "block_on_test_failure",
            "block_on_missing_tests",
        ],
        prefix="quality_gate",
    )

    execution = _require_object(data, "execution")

    workspace = _optional_object(execution, "workspace", prefix="execution.workspace")
    workspace.setdefault("mode", "temp")
    workspace.setdefault("base_dir", "")
    workspace.setdefault("cleanup_after_run", True)
    _validate_bool_fields(workspace, ["cleanup_after_run"], prefix="execution.workspace")

    install = _optional_object(execution, "install", prefix="execution.install")
    install.setdefault("enabled", True)
    install.setdefault("command", _default_install_command(project_type))
    _validate_bool_fields(install, ["enabled"], prefix="execution.install")
    _require_non_empty_string(install, "command", prefix="execution.install")

    test = _optional_object(execution, "test", prefix="execution.test")
    test.setdefault("enabled", True)
    test.setdefault("framework", _default_test_framework(project_type))
    test.setdefault("command", _default_test_command(project_type))
    test.setdefault("report_path", "")
    test.setdefault("timeout_seconds", 600)
    _validate_bool_fields(test, ["enabled"], prefix="execution.test")
    _require_non_empty_string(test, "framework", prefix="execution.test")
    _require_non_empty_string(test, "command", prefix="execution.test")
    _validate_positive_int(test, "timeout_seconds", prefix="execution.test")

    build = _optional_object(execution, "build", prefix="execution.build")
    build.setdefault("enabled", False)
    build.setdefault("command", "")
    _validate_bool_fields(build, ["enabled"], prefix="execution.build")

    deploy = _optional_object(execution, "deploy", prefix="execution.deploy")
    deploy.setdefault("enabled", intent == "deploy_project")
    deploy.setdefault("target", "docker")
    deploy.setdefault("command", "")
    _validate_bool_fields(deploy, ["enabled"], prefix="execution.deploy")

    if deploy["enabled"]:
        target = _require_non_empty_string(deploy, "target", prefix="execution.deploy")
        if target not in SUPPORTED_DEPLOY_TARGETS:
            raise TaskRequestValidationError(f"Unsupported execution.deploy.target: {target}")

        if target == "docker":
            docker = _require_object(deploy, "docker", prefix="execution.deploy")
            docker.setdefault("dockerfile_path", "Dockerfile")
            docker.setdefault("image_name", _repo_name_from_url(repo_url))
            docker.setdefault("image_tag", "latest")
            docker.setdefault("container_name", docker["image_name"])
            docker.setdefault("ports", [])
            docker.setdefault("env", {})
            _require_non_empty_string(docker, "dockerfile_path", prefix="execution.deploy.docker")
            _require_non_empty_string(docker, "image_name", prefix="execution.deploy.docker")
            _require_non_empty_string(docker, "image_tag", prefix="execution.deploy.docker")
            _require_non_empty_string(docker, "container_name", prefix="execution.deploy.docker")
            _validate_list(docker, "ports", prefix="execution.deploy.docker")
            _validate_object(docker, "env", prefix="execution.deploy.docker")
        else:
            deploy.setdefault("docker", None)

    monitoring = _optional_object(execution, "monitoring", prefix="execution.monitoring")
    monitoring.setdefault("enabled", False)
    monitoring.setdefault("type", "http")
    monitoring.setdefault("target", "")
    monitoring.setdefault("timeout_seconds", 60)
    _validate_bool_fields(monitoring, ["enabled"], prefix="execution.monitoring")
    _validate_positive_int(monitoring, "timeout_seconds", prefix="execution.monitoring")

    auth = _optional_object(data, "auth", prefix="auth")
    auth.setdefault("git_credential_type", "none")
    auth.setdefault("token_env_name", "")

    metadata = _optional_object(data, "metadata", prefix="metadata")
    metadata.setdefault("source", "unknown")
    metadata.setdefault("requested_by", "")
    metadata.setdefault("created_at", "")

    user_input = data.get("user_input", "")
    if user_input is not None and not isinstance(user_input, str):
        raise TaskRequestValidationError("user_input must be a string when provided.")

    return data


def _require_object(container: dict[str, Any], key: str, prefix: str | None = None) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        field = _field_name(key, prefix)
        raise TaskRequestValidationError(f"{field} must be an object.")
    return value


def _optional_object(container: dict[str, Any], key: str, prefix: str | None = None) -> dict[str, Any]:
    value = container.get(key)
    if value is None:
        container[key] = {}
        return container[key]
    if not isinstance(value, dict):
        field = _field_name(key, prefix)
        raise TaskRequestValidationError(f"{field} must be an object.")
    return value


def _require_non_empty_string(container: dict[str, Any], key: str, prefix: str | None = None) -> str:
    value = container.get(key)
    field = _field_name(key, prefix)
    if not isinstance(value, str) or not value.strip():
        raise TaskRequestValidationError(f"{field} must be a non-empty string.")
    return value.strip()


def _validate_positive_int(container: dict[str, Any], key: str, prefix: str | None = None) -> None:
    value = container.get(key)
    field = _field_name(key, prefix)
    if not isinstance(value, int) or value <= 0:
        raise TaskRequestValidationError(f"{field} must be a positive integer.")


def _validate_bool_fields(container: dict[str, Any], keys: list[str], prefix: str | None = None) -> None:
    for key in keys:
        value = container.get(key)
        field = _field_name(key, prefix)
        if not isinstance(value, bool):
            raise TaskRequestValidationError(f"{field} must be a boolean.")


def _validate_list(container: dict[str, Any], key: str, prefix: str | None = None) -> None:
    value = container.get(key)
    field = _field_name(key, prefix)
    if not isinstance(value, list):
        raise TaskRequestValidationError(f"{field} must be a list.")


def _validate_object(container: dict[str, Any], key: str, prefix: str | None = None) -> None:
    value = container.get(key)
    field = _field_name(key, prefix)
    if not isinstance(value, dict):
        raise TaskRequestValidationError(f"{field} must be an object.")


def _validate_repo_url(repo_url: str) -> None:
    parsed = urlparse(repo_url)
    if parsed.scheme not in {"http", "https", "ssh"} or not parsed.netloc:
        raise TaskRequestValidationError("project.repo_url must be a valid Git repository URL.")


def _field_name(key: str, prefix: str | None) -> str:
    return f"{prefix}.{key}" if prefix else key


def _default_build_system(project_type: str) -> str:
    mapping = {"python": "pip", "nodejs": "npm", "java": "maven"}
    return mapping.get(project_type, "")


def _default_install_command(project_type: str) -> str:
    mapping = {
        "python": "pip install -r requirements.txt",
        "nodejs": "npm install",
        "java": "mvn dependency:resolve",
    }
    return mapping.get(project_type, "")


def _default_test_framework(project_type: str) -> str:
    mapping = {"python": "pytest", "nodejs": "npm", "java": "maven"}
    return mapping.get(project_type, "")


def _default_test_command(project_type: str) -> str:
    mapping = {"python": "pytest", "nodejs": "npm test", "java": "mvn test"}
    return mapping.get(project_type, "")


def _repo_name_from_url(repo_url: str) -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    return repo_name or "app"
