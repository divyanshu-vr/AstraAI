"""In-process session store: short-term conversation threads, keyed by session_id.

Lives in memory on the local box. The client holds only the session_id and the new
message; the server keeps the thread and reconstructs a WINDOWED history for the LLM
(the model is stateless — it only knows what we put in the prompt). Old sessions are
not persisted; long-term memory (astra.memory) is what bridges across sessions.
"""

import threading
import time

_lock = threading.Lock()
_sessions: dict[str, list[dict]] = {}

_WINDOW = 6        # turns of history sent to the LLM (bounds token cost)
_MAX_SESSIONS = 200  # soft cap so a long-lived server can't grow unbounded


def append(session_id: str, question: str, answer: str, sources: list | None, skill: str) -> None:
    with _lock:
        if session_id not in _sessions and len(_sessions) >= _MAX_SESSIONS:
            _sessions.pop(next(iter(_sessions)))  # drop oldest-inserted
        _sessions.setdefault(session_id, []).append({
            "q": question, "a": answer, "sources": sources or [],
            "skill": skill, "t": time.strftime("%H:%M:%S"),
        })


def get(session_id: str) -> list[dict]:
    with _lock:
        return list(_sessions.get(session_id, []))


def reset(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)


def history_str(session_id: str) -> str | None:
    """Last _WINDOW turns formatted for the prompt (matches answer._enhance_query's
    'You: …' parsing). Answers are truncated to keep the window cheap."""
    turns = get(session_id)[-_WINDOW:]
    if not turns:
        return None
    return "\n".join(f"You: {t['q']}\nAstra: {t['a'][:500]}" for t in turns)
