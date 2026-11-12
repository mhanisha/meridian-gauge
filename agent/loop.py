"""The agent loop (owner: Neetu). Guide step 3b."""

SYSTEM_PROMPT = (
    "You are working in a Python repository at /work/repo. "
    "Make the change the user describes. You can run commands, read and edit files, "
    "and run the tests. There is no internet. Call finish when you are done."
)


def run_attempt(task_md: str, container: str, cfg: dict, model: str):
    """Loop until the model calls finish or a budget runs out.
    Return (ended, messages); ended is finished, step_limit, time_limit, cost_cap or error."""
    raise NotImplementedError
