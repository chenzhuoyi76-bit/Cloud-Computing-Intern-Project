import unittest
from unittest.mock import patch

from app import app


class LlmApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["OPENAI_API_KEY"] = "test-key"
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


if __name__ == "__main__":
    unittest.main()
