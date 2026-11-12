"""Start and stop one sandbox per attempt (owner: Neetu). Guide step 1b."""


def start_sandbox(repo_path: str, parent_sha: str, attempt_id: str, cfg: dict) -> str:
    """Make a throwaway copy of the repo at parent_sha, start a locked-down container
    with it mounted at /work/repo, and return the container name."""
    raise NotImplementedError


def stop_sandbox(container: str) -> None:
    """Remove the container and its repo copy. Must be safe to call twice."""
    raise NotImplementedError
