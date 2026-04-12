import unittest
from unittest.mock import patch

from app import app


class LlmApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["OPENAI_API_KEY"] = "test-key"
        app.config["TASK_WORKSPACE_ROOT"] = "runtime/workspaces-test"
        self.client = app.test_client()

    def test_missing_user_input_returns_400(self):
        response = self.client.post("/api/llm/intent", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "user_input is required")

    @patch("backend.routes.llm.recognize_intent")
    def test_detect_intent_success(self, mock_recognize_intent):
        mock_recognize_intent.return_value = {
            "user_input": "帮我部署项目",
            "intent": "deploy_project",
            "confidence": 0.95,
            "reason": "用户明确提出部署诉求",
            "suggested_action": "进入部署任务编排流程",
            "model": "gpt-4.1-mini",
        }

        response = self.client.post("/api/llm/intent", json={"user_input": "帮我部署项目"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["intent"], "deploy_project")

    @patch("backend.routes.dispatch.recognize_intent")
    def test_dispatch_blocks_deploy_when_tests_not_passed(self, mock_recognize_intent):
        mock_recognize_intent.return_value = {
            "user_input": "帮我部署项目",
            "intent": "deploy_project",
            "confidence": 0.95,
            "reason": "用户明确提出部署诉求",
            "suggested_action": "进入部署任务编排流程",
            "model": "gpt-4.1-mini",
        }

        response = self.client.post(
            "/api/llm/dispatch",
            json={"user_input": "帮我部署项目", "context": {"unit_tests_passed": False}},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["dispatch_result"]["status"], "blocked")
        self.assertEqual(body["dispatch_result"]["blocking_reason"], "unit_tests_not_passed")

    @patch("backend.routes.dispatch.recognize_intent")
    def test_dispatch_allows_deploy_when_tests_passed(self, mock_recognize_intent):
        mock_recognize_intent.return_value = {
            "user_input": "帮我部署项目",
            "intent": "deploy_project",
            "confidence": 0.95,
            "reason": "用户明确提出部署诉求",
            "suggested_action": "进入部署任务编排流程",
            "model": "gpt-4.1-mini",
        }

        response = self.client.post(
            "/api/llm/dispatch",
            json={"user_input": "帮我部署项目", "context": {"unit_tests_passed": True}},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["dispatch_result"]["status"], "ready")
        self.assertFalse(body["dispatch_result"]["blocked"])

    @patch("backend.routes.dispatch.recognize_intent")
    def test_dispatch_marks_run_test_ready(self, mock_recognize_intent):
        mock_recognize_intent.return_value = {
            "user_input": "帮我跑单元测试",
            "intent": "run_test",
            "confidence": 0.98,
            "reason": "用户要求执行测试",
            "suggested_action": "进入测试流程",
            "model": "gpt-4.1-mini",
        }

        response = self.client.post("/api/llm/dispatch", json={"user_input": "帮我跑单元测试"})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["dispatch_result"]["task"], "run_unit_tests")
        self.assertEqual(body["dispatch_result"]["status"], "ready")

    def test_prepare_task_rejects_invalid_payload(self):
        response = self.client.post("/api/tasks/prepare", json={"intent": "deploy_project"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("project must be an object", response.get_json()["error"])

    @patch("backend.routes.tasks.prepare_repository")
    def test_prepare_task_success(self, mock_prepare_repository):
        mock_prepare_repository.return_value = {
            "workspace_path": "runtime/workspaces-test/task_123",
            "repo_path": "runtime/workspaces-test/task_123/demo",
            "repo_name": "demo",
            "repo_url": "https://github.com/example/demo.git",
            "branch": "main",
            "checked_out_ref": "main",
        }

        payload = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/demo.git",
                "project_type": "python"
            },
            "execution": {
                "deploy": {
                    "enabled": True,
                    "target": "docker",
                    "docker": {}
                }
            }
        }

        response = self.client.post("/api/tasks/prepare", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["repository"]["repo_name"], "demo")
        self.assertEqual(body["task_request"]["project"]["branch"], "main")

    @patch("backend.routes.tasks.create_task_execution_record")
    @patch("backend.routes.tasks.execute_task_pipeline")
    def test_execute_task_ready_when_tests_pass(self, mock_execute_task_pipeline, mock_create_record):
        mock_execute_task_pipeline.return_value = {
            "status": "deployed",
            "message": "任务执行完成，部署已成功。",
            "repository": {
                "repo_path": "runtime/workspaces-test/task_123/demo"
            },
            "install_result": {
                "status": "passed"
            },
            "test_result": {
                "status": "passed"
            },
            "deploy_result": {
                "status": "passed",
                "target": "docker"
            },
            "dispatch_result": {
                "status": "ready",
                "blocked": False,
                "task": "deploy_project"
            },
        }
        mock_create_record.return_value = {"id": 1, "status": "deployed"}

        payload = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/demo.git",
                "project_type": "python"
            },
            "execution": {
                "deploy": {
                    "enabled": True,
                    "target": "docker",
                    "docker": {}
                }
            }
        }

        response = self.client.post("/api/tasks/execute", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "deployed")
        self.assertEqual(body["deploy_result"]["status"], "passed")
        self.assertEqual(body["history_record"]["id"], 1)

    @patch("backend.routes.tasks.execute_task_pipeline")
    @patch("backend.routes.tasks.create_task_execution_record")
    def test_execute_task_blocked_when_tests_fail(self, mock_create_record, mock_execute_task_pipeline):
        mock_execute_task_pipeline.return_value = {
            "status": "blocked",
            "message": "单元测试未通过，已触发质量门禁。",
            "repository": {
                "repo_path": "runtime/workspaces-test/task_123/demo"
            },
            "install_result": {
                "status": "passed"
            },
            "test_result": {
                "status": "failed",
                "returncode": 1
            },
            "deploy_result": None,
            "dispatch_result": {
                "status": "blocked",
                "blocked": True,
                "blocking_reason": "unit_tests_not_passed"
            },
        }
        mock_create_record.return_value = {"id": 2, "status": "blocked"}

        payload = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/demo.git",
                "project_type": "python"
            },
            "execution": {
                "deploy": {
                    "enabled": True,
                    "target": "docker",
                    "docker": {}
                }
            }
        }

        response = self.client.post("/api/tasks/execute", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "blocked")
        self.assertEqual(body["dispatch_result"]["blocking_reason"], "unit_tests_not_passed")
        self.assertEqual(body["history_record"]["id"], 2)

    @patch("backend.routes.tasks.list_task_execution_records")
    def test_list_task_history(self, mock_list_records):
        mock_list_records.return_value = [
            {"id": 2, "status": "blocked"},
            {"id": 1, "status": "deployed"},
        ]

        response = self.client.get("/api/tasks/history?limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["records"]), 2)

    @patch("backend.routes.tasks.get_task_execution_record")
    def test_get_task_history_record(self, mock_get_record):
        mock_get_record.return_value = {"id": 1, "status": "deployed"}

        response = self.client.get("/api/tasks/history/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["id"], 1)


if __name__ == "__main__":
    unittest.main()
