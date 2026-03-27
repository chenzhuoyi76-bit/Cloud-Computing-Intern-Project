from pathlib import Path
from typing import Any

from backend.services.repo_fetcher import prepare_repository
from backend.services.task_dispatcher import dispatch_task
from backend.services.test_runner_factory import get_test_runner
from backend.services.test_runners.base import TestExecutionError, UnsupportedProjectTypeError


def execute_task_pipeline(task_request: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    repository = prepare_repository(task_request=task_request, workspace_root=workspace_root)
    repo_path = Path(repository["repo_path"])
    project = task_request["project"]
    execution = task_request["execution"]

    install_result = None
    test_result = None

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
        return {
            "status": "failed",
            "message": str(exc),
            "repository": repository,
            "install_result": install_result,
            "test_result": test_result,
            "dispatch_result": dispatch_task(
                intent_result={"intent": task_request["intent"]},
                context={"unit_tests_passed": False},
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

    return {
        "status": overall_status,
        "message": _build_message(
            install_result=install_result,
            test_result=test_result,
            dispatch_result=dispatch_result,
        ),
        "repository": repository,
        "install_result": install_result,
        "test_result": test_result,
        "dispatch_result": dispatch_result,
    }


def _build_message(
    install_result: dict[str, Any] | None,
    test_result: dict[str, Any] | None,
    dispatch_result: dict[str, Any],
) -> str:
    if install_result and install_result["status"] == "failed":
        return "依赖安装失败，流程已停止。"
    if test_result and test_result["status"] == "failed":
        return "单元测试未通过，已触发质量门禁。"
    if dispatch_result.get("blocked"):
        return "流程被质量门禁阻塞。"
    return "任务执行完成，可以进入下一阶段。"
