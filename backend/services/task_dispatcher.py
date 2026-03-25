from typing import Any


TEST_GATE_REQUIRED_INTENTS = {"deploy_project", "package_project", "merge_code"}


def dispatch_task(intent_result: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    intent = intent_result.get("intent", "unknown")
    unit_tests_passed = bool(context.get("unit_tests_passed", False))

    if intent == "run_test":
        return {
            "task": "run_unit_tests",
            "status": "ready",
            "blocked": False,
            "stage": "quality_gate",
            "message": "进入单元测试执行阶段。",
            "required_checks": ["unit_tests"],
            "next_steps": ["执行项目单元测试", "收集测试报告", "根据结果决定是否继续后续流程"],
        }

    if intent in TEST_GATE_REQUIRED_INTENTS:
        if not unit_tests_passed:
            return {
                "task": _task_name_for_intent(intent),
                "status": "blocked",
                "blocked": True,
                "stage": "quality_gate",
                "message": "单元测试是强制卡点，测试未通过前不能继续当前流程。",
                "required_checks": ["unit_tests"],
                "blocking_reason": "unit_tests_not_passed",
                "next_steps": ["先执行单元测试", "确认测试通过", "测试通过后重新发起当前任务"],
                "policy": "deploy/package/merge 必须先通过单元测试",
            }

        return {
            "task": _task_name_for_intent(intent),
            "status": "ready",
            "blocked": False,
            "stage": "execution",
            "message": "单元测试已通过，可以进入后续执行阶段。",
            "required_checks": ["unit_tests"],
            "next_steps": _next_steps_for_intent(intent),
            "policy": "deploy/package/merge 必须先通过单元测试",
        }

    if intent == "check_service_status":
        return {
            "task": "check_service_status",
            "status": "ready",
            "blocked": False,
            "stage": "monitoring",
            "message": "进入服务状态检查流程。",
            "required_checks": [],
            "next_steps": ["查询服务运行状态", "返回监控结果摘要"],
        }

    if intent == "summarize_monitoring":
        return {
            "task": "summarize_monitoring",
            "status": "ready",
            "blocked": False,
            "stage": "monitoring",
            "message": "进入监控汇总流程。",
            "required_checks": [],
            "next_steps": ["读取监控数据", "生成状态摘要与建议"],
        }

    return {
        "task": "manual_review",
        "status": "needs_review",
        "blocked": False,
        "stage": "triage",
        "message": "暂时无法自动分发，请人工确认任务类型。",
        "required_checks": [],
        "next_steps": ["补充更明确的任务描述", "或由人工选择具体流程"],
    }


def _task_name_for_intent(intent: str) -> str:
    mapping = {
        "deploy_project": "deploy_project",
        "package_project": "package_project",
        "merge_code": "merge_code",
    }
    return mapping.get(intent, intent)


def _next_steps_for_intent(intent: str) -> list[str]:
    mapping = {
        "deploy_project": ["准备部署配置", "执行部署任务", "执行部署后状态检查"],
        "package_project": ["准备构建环境", "执行打包流程", "归档构建产物"],
        "merge_code": ["检查分支状态", "执行合并流程", "记录合并结果"],
    }
    return mapping.get(intent, ["进入任务执行流程"])
