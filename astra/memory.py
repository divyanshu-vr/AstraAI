"""Long-term memory — per-user typed facts, persisted across sessions.

Structured-memory model (inspired by MemU) on Astra's own stack: after each chat
exchange a Groq call distills DURABLE facts (profile | event | knowledge); each is
embedded with FastEmbed and stored in a dedicated Chroma collection, namespaced by
user_id. Before answering, the facts most relevant to the new question are recalled
and injected into the prompt. Best-effort throughout: a failure here never breaks chat.
"""

import json
import re
import time
import uuid

from astra import embeddings, llm, store

_TYPES = {"profile", "event", "knowledge"}

_EXTRACT_SYSTEM = (
    "Extract DURABLE facts about the USER (the person asking) worth remembering across future "
    "sessions, from one exchange between the user and an assistant about a software codebase. "
    'Return a JSON array (possibly empty) of objects {"type", "text"} where type is one of: '
    "profile (who the user is: their name, role, team, the repo/module THEY work on, their stated preferences), "
    "event (something the USER did, decided, or a task the user is currently working on), "
    "knowledge (a conclusion the USER reached or something they explicitly want remembered). "
    "CRITICAL: record facts about the USER only. Do NOT store general facts about the codebase, "
    "repositories, files, or who-owns-what — those are not memories about the user. "
    "Each 'text' must be ONE concise self-contained sentence naming the user (e.g. 'The user…' or their name). "
    "Skip greetings, one-off lookups, and anything ephemeral. "
    "If nothing about the user is worth remembering, return []. Output ONLY the JSON array, nothing else."
)


def _parse(raw: str) -> list[dict]:
    m = re.search(r"\[.*\]", raw or "", re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except (ValueError, TypeError):
        return []
    out = []
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and str(it.get("text", "")).strip():
            t = it.get("type", "knowledge")
            out.append({
                "type": t if t in _TYPES else "knowledge",
                "text": str(it["text"]).strip()[:300],
            })
    return out[:8]


def remember(user_id: str | None, user_msg: str, assistant_msg: str) -> None:
    """Extract + persist durable facts from one exchange. Call in a background thread."""
    if not user_id:
        return
    try:
        raw = llm.complete(_EXTRACT_SYSTEM, f"USER: {user_msg}\n\nASSISTANT: {assistant_msg}")
        facts = _parse(raw)
        if not facts:
            return
        texts = [f["text"] for f in facts]
        ts = int(time.time())
        store.get_memory_collection().add(
            ids=[f"mem::{user_id}::{uuid.uuid4().hex[:12]}" for _ in facts],
            documents=texts,
            embeddings=embeddings.embed_documents(texts),
            metadatas=[{"user_id": user_id, "type": f["type"], "ts": ts} for f in facts],
        )
    except Exception:  # noqa: BLE001 — memory is best-effort; never break the chat
        pass


def recall(user_id: str | None, query: str, k: int = 5) -> str:
    """Return the user's most relevant remembered facts as bullet lines, or '' if none."""
    if not user_id:
        return ""
    try:
        qvec = embeddings.embed_query(query)
        res = store.get_memory_collection().query(
            query_embeddings=[qvec], n_results=k,
            where={"user_id": user_id}, include=["documents", "metadatas"],
        )
    except Exception:  # noqa: BLE001 — a cold/empty memory store must not break chat
        return ""
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    if not docs:
        return ""
    return "\n".join(f"- ({m.get('type', 'note')}) {d}" for d, m in zip(docs, metas))


def format_block(mem: str) -> str:
    """Wrap recalled facts in a labelled block for prompt injection, or '' if empty."""
    return f"ABOUT THIS USER (remembered from past sessions):\n{mem}\n\n" if mem else ""
