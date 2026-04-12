import json
from typing import Any

from backend.db import get_session
from backend.models.task_record import TaskExecutionRecord


def create_task_execution_record(task_request: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    session = get_session()
    try:
        record = TaskExecutionRecord(
            intent=task_request["intent"],
            repo_url=task_request["project"]["repo_url"],
            project_type=task_request["project"]["project_type"],
            status=execution_result["status"],
            message=execution_result["message"],
            repository_json=json.dumps(execution_result.get("repository") or {}, ensure_ascii=False),
            task_request_json=json.dumps(task_request, ensure_ascii=False),
            install_result_json=json.dumps(execution_result.get("install_result"), ensure_ascii=False),
            test_result_json=json.dumps(execution_result.get("test_result"), ensure_ascii=False),
            deploy_result_json=json.dumps(execution_result.get("deploy_result"), ensure_ascii=False),
            dispatch_result_json=json.dumps(execution_result.get("dispatch_result") or {}, ensure_ascii=False),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return serialize_task_execution_record(record)
    finally:
        session.close()


def list_task_execution_records(limit: int = 20) -> list[dict[str, Any]]:
    session = get_session()
    try:
        records = (
            session.query(TaskExecutionRecord)
            .order_by(TaskExecutionRecord.created_at.desc(), TaskExecutionRecord.id.desc())
            .limit(limit)
            .all()
        )
        return [serialize_task_execution_record(record, include_payloads=False) for record in records]
    finally:
        session.close()


def get_task_execution_record(record_id: int) -> dict[str, Any] | None:
    session = get_session()
    try:
        record = session.get(TaskExecutionRecord, record_id)
        if record is None:
            return None
        return serialize_task_execution_record(record)
    finally:
        session.close()


def serialize_task_execution_record(record: TaskExecutionRecord, include_payloads: bool = True) -> dict[str, Any]:
    data = {
        "id": record.id,
        "intent": record.intent,
        "repo_url": record.repo_url,
        "project_type": record.project_type,
        "status": record.status,
        "message": record.message,
        "created_at": record.created_at.isoformat(),
    }
    if include_payloads:
        data.update(
            {
                "repository": json.loads(record.repository_json),
                "task_request": json.loads(record.task_request_json),
                "install_result": json.loads(record.install_result_json),
                "test_result": json.loads(record.test_result_json),
                "deploy_result": json.loads(record.deploy_result_json),
                "dispatch_result": json.loads(record.dispatch_result_json),
            }
        )
    return data
