"""Entry point: python -m orchestrator config.yaml. Guide step 4."""
import sys


def main(config_path: str) -> None:
    """Load the config, create the run folder, then for each task and model:
    build the answer key, run the agent in a fresh sandbox, grade, and clean up.
    Skip anything whose result.json already exists."""
    raise NotImplementedError


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
