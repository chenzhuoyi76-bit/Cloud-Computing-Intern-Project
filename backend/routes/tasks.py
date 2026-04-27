from flask import Blueprint, current_app, jsonify, request

from backend.schemas.task_request import TaskRequestValidationError, validate_task_request
from backend.services.repo_fetcher import RepoFetchError, prepare_repository
from backend.services.task_executor import execute_task_pipeline
from backend.services.task_history_service import (
    create_task_execution_record,
    get_task_execution_record,
    list_task_execution_records,
)

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

    history_record = create_task_execution_record(validated_request, result)
    return jsonify(
        {
            "task_request": validated_request,
            "history_record": _build_history_record_summary(history_record),
            **result,
        }
    )


@tasks_bp.get("/history")
def list_task_history():
    limit_arg = request.args.get("limit", "20")
    try:
        limit = max(1, min(int(limit_arg), 100))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    return jsonify({"records": list_task_execution_records(limit=limit)})


@tasks_bp.get("/history/<int:record_id>")
def get_task_history(record_id: int):
    record = get_task_execution_record(record_id)
    if record is None:
        return jsonify({"error": "record not found"}), 404
    return jsonify(record)


def _build_history_record_summary(history_record: dict) -> dict:
    return {
        "id": history_record.get("id"),
        "status": history_record.get("status"),
        "created_at": history_record.get("created_at"),
        "summary": history_record.get("summary", ""),
    }
