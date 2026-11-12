"""Build the comparison report from a run folder (owner: Varsha). Guide step 7."""


def load_results(run_dir: str):
    """Return one row per task and model, joining attempt.json and result.json."""
    raise NotImplementedError


def failure_category(row: dict) -> str:
    """solved, infrastructure, ran out of budget, broke an existing test,
    wording only, or needs review."""
    raise NotImplementedError
