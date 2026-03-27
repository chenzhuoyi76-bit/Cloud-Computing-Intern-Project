from backend.services.test_runners.base import UnsupportedProjectTypeError
from backend.services.test_runners.python_runner import PythonTestRunner


def get_test_runner(project_type: str):
    runners = {
        "python": PythonTestRunner(),
    }
    runner = runners.get(project_type)
    if runner is None:
        raise UnsupportedProjectTypeError(
            f"No test runner is implemented yet for project type: {project_type}"
        )
    return runner
