import unittest

from backend.services.deployers.base import DeploymentError
from backend.services.deployers.docker_deployer import _format_port_mapping


class DockerDeployerTestCase(unittest.TestCase):
    def test_format_string_port_mapping(self):
        self.assertEqual(_format_port_mapping("3001:3000"), "3001:3000")

    def test_format_object_port_mapping(self):
        self.assertEqual(
            _format_port_mapping({"host": 3001, "container": 3000}),
            "3001:3000",
        )

    def test_format_object_port_mapping_with_protocol(self):
        self.assertEqual(
            _format_port_mapping({"host": 3001, "container": 3000, "protocol": "tcp"}),
            "3001:3000/tcp",
        )

    def test_reject_invalid_port_mapping(self):
        with self.assertRaises(DeploymentError):
            _format_port_mapping({"host": 3001})


if __name__ == "__main__":
    unittest.main()
