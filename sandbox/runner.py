"""Run tests in a sandbox and read the results (owner: Keerthana). Guide steps 1c and 1d."""


def run_tests(container: str, test_paths: list[str], timeout: int = 900) -> dict[str, str]:
    """Run the given tests and return {test_id: "passed" | "failed" | "skipped"}."""
    raise NotImplementedError


def build_answer_key(task: dict, task_dir: str) -> None:
    """Answer-key mode: write answer_key.json, or mark the task dropped with a reason."""
    raise NotImplementedError


def grade(task: dict, attempt_dir: str) -> None:
    """Grade mode: apply patch.diff, then the hidden tests, and write result.json."""
    raise NotImplementedError
