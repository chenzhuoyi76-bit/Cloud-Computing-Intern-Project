from flask import Blueprint, current_app, jsonify, request

from backend.schemas.task_request import TaskRequestValidationError, validate_task_request
from backend.services.repo_fetcher import RepoFetchError, prepare_repository
from backend.services.task_executor import execute_task_pipeline

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


@tasks_bp.post("/prepare")
def prepare_task():
    payload = request.get_json(silent=True) or {}

    try:
        validated_request = validate_task_request(payload)
    except TaskRequestValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        repository = prepare_repository(
            task_request=validated_request,
            workspace_root=current_app.config["TASK_WORKSPACE_ROOT"],
        )
    except RepoFetchError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(
        {
            "status": "ready",
            "message": "任务请求校验通过，仓库已拉取到本地工作目录。",
            "task_request": validated_request,
            "repository": repository,
        }
    )


@tasks_bp.post("/execute")
def execute_task():
    payload = request.get_json(silent=True) or {}

    try:
        validated_request = validate_task_request(payload)
    except TaskRequestValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = execute_task_pipeline(
            task_request=validated_request,
            workspace_root=current_app.config["TASK_WORKSPACE_ROOT"],
        )
    except RepoFetchError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"task_request": validated_request, **result})
