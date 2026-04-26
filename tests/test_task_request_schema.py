import unittest

from backend.schemas.task_request import TaskRequestValidationError, validate_task_request


class TaskRequestSchemaTestCase(unittest.TestCase):
    def test_validate_minimal_python_deploy_request(self):
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

        validated = validate_task_request(payload)

        self.assertEqual(validated["project"]["branch"], "main")
        self.assertEqual(validated["execution"]["install"]["command"], "pip install -r requirements.txt")
        self.assertEqual(validated["execution"]["test"]["command"], "python -m pytest")
        self.assertEqual(validated["execution"]["deploy"]["docker"]["image_name"], "demo")
        self.assertTrue(validated["quality_gate"]["unit_tests_required"])

    def test_validate_minimal_nodejs_deploy_request(self):
        payload = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/node-demo.git",
                "project_type": "nodejs"
            },
            "execution": {
                "deploy": {
                    "enabled": True,
                    "target": "docker",
                    "docker": {}
                }
            }
        }

        validated = validate_task_request(payload)

        self.assertEqual(validated["project"]["build_system"], "npm")
        self.assertEqual(validated["execution"]["install"]["command"], "npm install")
        self.assertEqual(validated["execution"]["test"]["framework"], "npm")
        self.assertEqual(validated["execution"]["test"]["command"], "npm test")

    def test_validate_minimal_java_deploy_request(self):
        payload = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/java-demo.git",
                "project_type": "java"
            },
            "execution": {
                "deploy": {
                    "enabled": True,
                    "target": "docker",
                    "docker": {}
                }
            }
        }

        validated = validate_task_request(payload)

        self.assertEqual(validated["project"]["build_system"], "maven")
        self.assertEqual(validated["execution"]["install"]["command"], "mvn dependency:resolve")
        self.assertEqual(validated["execution"]["test"]["framework"], "maven")
        self.assertEqual(validated["execution"]["test"]["command"], "mvn test")

    def test_normalize_docker_names_to_lowercase(self):
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
                    "docker": {
                        "image_name": "DemoIDE",
                        "image_tag": "latest",
                        "container_name": "Demo IDE",
                    }
                }
            }
        }

        validated = validate_task_request(payload)

        self.assertEqual(validated["execution"]["deploy"]["docker"]["image_name"], "demoide")
        self.assertEqual(validated["execution"]["deploy"]["docker"]["container_name"], "demo-ide")

    def test_reject_missing_repo_url(self):
        payload = {
            "intent": "deploy_project",
            "project": {
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

        with self.assertRaises(TaskRequestValidationError):
            validate_task_request(payload)

    def test_reject_invalid_project_type(self):
        payload = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/demo.git",
                "project_type": "php"
            },
            "execution": {
                "deploy": {
                    "enabled": True,
                    "target": "docker",
                    "docker": {}
                }
            }
        }

        with self.assertRaises(TaskRequestValidationError):
            validate_task_request(payload)

    def test_reject_missing_docker_config_when_deploy_enabled(self):
        payload = {
            "intent": "deploy_project",
            "project": {
                "repo_url": "https://github.com/example/demo.git",
                "project_type": "python"
            },
            "execution": {
                "deploy": {
                    "enabled": True,
                    "target": "docker"
                }
            }
        }

        with self.assertRaises(TaskRequestValidationError):
            validate_task_request(payload)


if __name__ == "__main__":
    unittest.main()
