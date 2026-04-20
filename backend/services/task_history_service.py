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
    repository = json.loads(record.repository_json)
    install_result = json.loads(record.install_result_json)
    test_result = json.loads(record.test_result_json)
    deploy_result = json.loads(record.deploy_result_json)
    dispatch_result = json.loads(record.dispatch_result_json)
    monitoring_result = None
    if isinstance(deploy_result, dict):
        monitoring_result = deploy_result.get("monitoring_result")

    data = {
        "id": record.id,
        "intent": record.intent,
        "repo_url": record.repo_url,
        "project_type": record.project_type,
        "status": record.status,
        "message": record.message,
        "created_at": record.created_at.isoformat(),
        "status_overview": _build_status_overview(
            overall_status=record.status,
            repository=repository,
            install_result=install_result,
            test_result=test_result,
            deploy_result=deploy_result,
            monitoring_result=monitoring_result,
            dispatch_result=dispatch_result,
        ),
        "timings": _build_timings(
            repository=repository,
            install_result=install_result,
            test_result=test_result,
            deploy_result=deploy_result,
            monitoring_result=monitoring_result,
        ),
        "summary": _build_summary(
            status=record.status,
            status_overview=_build_status_overview(
                overall_status=record.status,
                repository=repository,
                install_result=install_result,
                test_result=test_result,
                deploy_result=deploy_result,
                monitoring_result=monitoring_result,
                dispatch_result=dispatch_result,
            ),
            monitoring_result=monitoring_result,
        ),
    }
    if include_payloads:
        data.update(
            {
                "repository": repository,
                "task_request": json.loads(record.task_request_json),
                "install_result": install_result,
                "test_result": test_result,
                "deploy_result": deploy_result,
                "monitoring_result": monitoring_result,
                "dispatch_result": dispatch_result,
            }
        )
    return data


def _build_status_overview(
    overall_status: str,
    repository: dict[str, Any] | None,
    install_result: dict[str, Any] | None,
    test_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    monitoring_result: dict[str, Any] | None,
    dispatch_result: dict[str, Any] | None,
) -> dict[str, str]:
    return {
        "overall": overall_status,
        "repository": _step_status(repository, default="unknown"),
        "install": _step_status(install_result, default="skipped"),
        "test": _step_status(test_result, default="skipped"),
        "quality_gate": (dispatch_result or {}).get("status", "unknown"),
        "deploy": _step_status(deploy_result, default="skipped"),
        "monitoring": _step_status(monitoring_result, default="skipped"),
    }


def _build_timings(
    repository: dict[str, Any] | None,
    install_result: dict[str, Any] | None,
    test_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    monitoring_result: dict[str, Any] | None,
) -> dict[str, float | None]:
    repository_duration = _step_duration(repository)
    install_duration = _step_duration(install_result)
    test_duration = _step_duration(test_result)
    deploy_duration = _step_duration(deploy_result)
    monitoring_duration = _step_duration(monitoring_result)
    return {
        "repository": repository_duration,
        "install": install_duration,
        "test": test_duration,
        "deploy": deploy_duration,
        "monitoring": monitoring_duration,
        "total": round(
            sum(
                duration or 0
                for duration in (
                    repository_duration,
                    install_duration,
                    test_duration,
                    deploy_duration,
                    monitoring_duration,
                )
            ),
            3,
        ),
    }


def _step_status(step_result: dict[str, Any] | None, default: str) -> str:
    if not step_result:
        return default
    return step_result.get("status", default)


def _step_duration(step_result: dict[str, Any] | None) -> float | None:
    if not step_result:
        return None
    return step_result.get("duration_seconds")


def _build_summary(
    status: str,
    status_overview: dict[str, str],
    monitoring_result: dict[str, Any] | None,
) -> str:
    parts = [f"整体：{status}"]
    parts.append(f"测试：{status_overview.get('test', 'unknown')}")
    parts.append(f"部署：{status_overview.get('deploy', 'unknown')}")
    monitoring_status = status_overview.get("monitoring", "unknown")
    if monitoring_status != "skipped":
        parts.append(f"监测：{monitoring_status}")
    if monitoring_result and monitoring_result.get("container_status"):
        parts.append(f"容器：{monitoring_result['container_status']}")
    return "｜".join(parts)
