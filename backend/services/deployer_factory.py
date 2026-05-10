from backend.services.deployers.base import UnsupportedDeployTargetError
from backend.services.deployers.docker_deployer import DockerDeployer
from backend.services.deployers.server_deployer import ServerDeployer


def get_deployer(target: str):
    deployers = {
        "docker": DockerDeployer(),
        "server": ServerDeployer(),
    }
    deployer = deployers.get(target)
    if deployer is None:
        raise UnsupportedDeployTargetError(
            f"No deployer is implemented yet for target: {target}"
        )
    return deployer
