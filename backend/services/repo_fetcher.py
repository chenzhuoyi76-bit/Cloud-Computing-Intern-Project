import re
import subprocess
from pathlib import Path
from tempfile import mkdtemp
from typing import Any


class RepoFetchError(Exception):
    """Raised when the repository fetch step fails."""


def prepare_repository(task_request: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    project = task_request["project"]
    repo_url = project["repo_url"]
    branch = project.get("branch", "main")
    commit_sha = project.get("commit_sha", "")

    workspace_root_path = Path(workspace_root)
    workspace_root_path.mkdir(parents=True, exist_ok=True)

    task_workspace = Path(mkdtemp(prefix="task_", dir=str(workspace_root_path)))
    repo_name = _safe_repo_name(repo_url)
    repo_path = task_workspace / repo_name

    clone_cmd = [
        "git",
        "clone",
        "--branch",
        branch,
        "--depth",
        "1",
        repo_url,
        str(repo_path),
    ]
    _run_command(clone_cmd, cwd=task_workspace)

    checked_out_ref = branch
    if commit_sha:
        _run_command(["git", "checkout", commit_sha], cwd=repo_path)
        checked_out_ref = commit_sha

    return {
        "workspace_path": str(task_workspace),
        "repo_path": str(repo_path),
        "repo_name": repo_name,
        "repo_url": repo_url,
        "branch": branch,
        "checked_out_ref": checked_out_ref,
    }


def _run_command(command: list[str], cwd: Path) -> None:
    try:
        subprocess.run(
            command,
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RepoFetchError("git is not installed or not available in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or "Unknown git error"
        raise RepoFetchError(f"Failed to fetch repository: {detail}") from exc


def _safe_repo_name(repo_url: str) -> str:
    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    repo_name = re.sub(r"[^A-Za-z0-9._-]", "-", repo_name)
    return repo_name or "repository"
