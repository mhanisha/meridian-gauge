"""The five tools the model can use (owner: Neetu). Guide step 3a."""


def run(container: str, command: str, limit: int = 180) -> str:
    raise NotImplementedError


def read(container: str, path: str) -> str:
    raise NotImplementedError


def write(container: str, path: str, content: str) -> str:
    raise NotImplementedError


def replace(container: str, path: str, old: str, new: str) -> str:
    raise NotImplementedError


HANDLERS = {"run": run, "read": read, "write": write, "replace": replace}
TOOLS: list[dict] = []  # tool descriptions sent to the model; see the guide
