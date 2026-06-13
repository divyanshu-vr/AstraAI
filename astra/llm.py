"""Groq chat client (answer generation). Verified call shape: client.chat.completions.create."""

from groq import Groq

from astra import config

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        config.require_keys()
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def complete(system: str, user: str, stream: bool = False):
    """Single-turn completion. Returns full text, or a generator of chunks if stream=True."""
    client = _get_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if stream:
        return _stream(client, messages)
    resp = client.chat.completions.create(model=config.LLM_MODEL, messages=messages)
    return resp.choices[0].message.content


def _stream(client, messages):
    for chunk in client.chat.completions.create(
        model=config.LLM_MODEL, messages=messages, stream=True
    ):
        yield chunk.choices[0].delta.content or ""
