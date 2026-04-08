from backend.services.deployers.base import UnsupportedDeployTargetError
from backend.services.deployers.docker_deployer import DockerDeployer


def get_deployer(target: str):
    deployers = {
        "docker": DockerDeployer(),
    }
    deployer = deployers.get(target)
    if deployer is None:
        raise UnsupportedDeployTargetError(
            f"No deployer is implemented yet for target: {target}"
        )
    return deployer
