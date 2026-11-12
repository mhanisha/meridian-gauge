"""One function to reach any model (owner: Neetu). Guide step 2."""


def chat(cfg: dict, model_name: str, messages: list[dict], tools: list[dict]):
    """Send one request. Return (message, log) where log has tokens_in, tokens_out,
    cost_usd, seconds and model_served. Raise if the served model is not model_name."""
    raise NotImplementedError
