from pathlib import Path
from time import perf_counter
from typing import Any

from backend.services.deployer_factory import get_deployer
from backend.services.deployers.base import DeploymentError, UnsupportedDeployTargetError
from backend.services.repo_fetcher import prepare_repository
from backend.services.task_dispatcher import dispatch_task
from backend.services.test_runner_factory import get_test_runner
from backend.services.test_runners.base import TestExecutionError, UnsupportedProjectTypeError


def execute_task_pipeline(task_request: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    pipeline_started_at = perf_counter()
    repository = prepare_repository(task_request=task_request, workspace_root=workspace_root)
    repo_path = Path(repository["repo_path"])
    project = task_request["project"]
    execution = task_request["execution"]

    install_result = None
    test_result = None
    deploy_result = None

    try:
        runner = get_test_runner(project["project_type"])

        if execution["install"]["enabled"]:
            install_result = runner.install_dependencies(
                repo_path=repo_path,
                install_config=execution["install"],
                project=project,
            )

        if execution["test"]["enabled"]:
            test_result = runner.run_tests(
                repo_path=repo_path,
                test_config=execution["test"],
                project=project,
            )
    except (UnsupportedProjectTypeError, TestExecutionError) as exc:
        dispatch_result = dispatch_task(
            intent_result={"intent": task_request["intent"]},
            context={"unit_tests_passed": False},
        )
        overall_status = "failed"
        return {
            "status": overall_status,
            "message": str(exc),
            "repository": repository,
            "install_result": install_result,
            "test_result": test_result,
            "deploy_result": deploy_result,
            "dispatch_result": dispatch_result,
            "status_overview": _build_status_overview(
                overall_status=overall_status,
                repository=repository,
                install_result=install_result,
                test_result=test_result,
                deploy_result=deploy_result,
                dispatch_result=dispatch_result,
            ),
            "timings": _build_timings(
                repository=repository,
                install_result=install_result,
                test_result=test_result,
                deploy_result=deploy_result,
                total_duration_seconds=round(perf_counter() - pipeline_started_at, 3),
            ),
        }

    unit_tests_passed = bool(test_result and test_result["status"] == "passed")
    dispatch_result = dispatch_task(
        intent_result={"intent": task_request["intent"]},
        context={"unit_tests_passed": unit_tests_passed},
    )

    overall_status = "ready" if not dispatch_result.get("blocked", False) else "blocked"
    if install_result and install_result["status"] == "failed":
        overall_status = "failed"
    if test_result and test_result["status"] == "failed":
        overall_status = "blocked"

    if overall_status == "ready" and execution["deploy"]["enabled"]:
        try:
            deployer = get_deployer(execution["deploy"]["target"])
            deploy_result = deployer.deploy(
                repo_path=repo_path,
                deploy_config=execution["deploy"],
                project=project,
            )
            overall_status = "deployed"
        except (UnsupportedDeployTargetError, DeploymentError) as exc:
            overall_status = "failed"
            deploy_result = {
                "step": "deploy",
                "target": execution["deploy"]["target"],
                "status": "failed",
                "error": str(exc),
            }

    total_duration_seconds = round(perf_counter() - pipeline_started_at, 3)
    return {
        "status": overall_status,
        "message": _build_message(
            install_result=install_result,
            test_result=test_result,
            deploy_result=deploy_result,
            dispatch_result=dispatch_result,
        ),
        "repository": repository,
        "install_result": install_result,
        "test_result": test_result,
        "deploy_result": deploy_result,
        "dispatch_result": dispatch_result,
        "status_overview": _build_status_overview(
            overall_status=overall_status,
            repository=repository,
            install_result=install_result,
            test_result=test_result,
            deploy_result=deploy_result,
            dispatch_result=dispatch_result,
        ),
        "timings": _build_timings(
            repository=repository,
            install_result=install_result,
            test_result=test_result,
            deploy_result=deploy_result,
            total_duration_seconds=total_duration_seconds,
        ),
    }


def _build_message(
    install_result: dict[str, Any] | None,
    test_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    dispatch_result: dict[str, Any],
) -> str:
    if install_result and install_result["status"] == "failed":
        return "依赖安装失败，流程已停止。"
    if test_result and test_result["status"] == "failed":
        return "单元测试未通过，已触发质量门禁。"
    if dispatch_result.get("blocked"):
        return "流程被质量门禁阻塞。"
    if deploy_result and deploy_result.get("status") == "failed":
        return "部署执行失败。"
    if deploy_result and deploy_result.get("status") == "passed":
        return "任务执行完成，部署已成功。"
    return "任务执行完成，可以进入下一阶段。"


def _build_status_overview(
    overall_status: str,
    repository: dict[str, Any] | None,
    install_result: dict[str, Any] | None,
    test_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    dispatch_result: dict[str, Any] | None,
) -> dict[str, str]:
    return {
        "overall": overall_status,
        "repository": _step_status(repository, default="skipped"),
        "install": _step_status(install_result, default="skipped"),
        "test": _step_status(test_result, default="skipped"),
        "quality_gate": (dispatch_result or {}).get("status", "unknown"),
        "deploy": _step_status(deploy_result, default="skipped"),
    }


def _build_timings(
    repository: dict[str, Any] | None,
    install_result: dict[str, Any] | None,
    test_result: dict[str, Any] | None,
    deploy_result: dict[str, Any] | None,
    total_duration_seconds: float,
) -> dict[str, float | None]:
    return {
        "repository": _step_duration(repository),
        "install": _step_duration(install_result),
        "test": _step_duration(test_result),
        "deploy": _step_duration(deploy_result),
        "total": total_duration_seconds,
    }


def _step_status(step_result: dict[str, Any] | None, default: str) -> str:
    if not step_result:
        return default
    return step_result.get("status", default)


def _step_duration(step_result: dict[str, Any] | None) -> float | None:
    if not step_result:
        return None
    return step_result.get("duration_seconds")
