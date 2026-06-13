"""Build a cited answer from retrieved chunks via Groq.

Improvement over the reference (which just concatenated chunks): the LLM SYNTHESIZES
an answer grounded in the numbered sources, and we attach an accurate Sources list
from the retrieval metadata so [n] always points at a real file.
"""

from astra import llm, memory, workspace
from astra import retrieve as retr

SYSTEM = (
    "You are Astra, an onboarding assistant for a workspace of software repositories. "
    "Answer questions ABOUT THE CODE using ONLY the numbered sources (each tagged with its repo); "
    "cite every code claim with [n], and when sources span repos say which repo each fact comes from. "
    "An 'ABOUT THIS USER' block may also be present — facts Astra remembers about THIS USER across "
    "sessions. USE it to answer questions about the user themselves (their name, role, team, what "
    "they've been working on) and to personalize your reply. Don't cite it as a source and don't treat "
    "it as evidence about how the code works. "
    "If neither the sources nor the user block contain the answer, say so plainly — do not invent. "
    "Be clear and concise."
)


def _build_user(
    question: str, hits: list[dict], history: str | None = None, mem: str | None = None
) -> str:
    blocks = [
        f"[{i}] ({h.get('repo') or 'repo'}) {h['source']} (chunk {h['chunk_index']})\n{h['content']}"
        for i, h in enumerate(hits, 1)
    ]
    sources = "\n\n".join(blocks)
    convo = f"Conversation so far (context for follow-ups):\n{history}\n\n" if history else ""
    return (
        f"{memory.format_block(mem)}"
        f"{convo}"
        f"Question: {question}\n\n"
        f"Sources:\n{sources}\n\n"
        "Answer the question using inline [n] citations."
    )


_STOP = {
    "what", "how", "why", "when", "where", "which", "who", "does", "do", "is",
    "are", "the", "a", "an", "in", "on", "to", "of", "and", "or", "it", "this",
    "that", "you", "i", "we", "me", "my", "your", "astra",
}


def _enhance_query(question: str, history: str | None) -> str:
    """Follow-ups ("and where is that tested?") embed poorly alone — append key
    terms from the previous user turn to the retrieval query (reference pattern)."""
    if not history:
        return question
    prev_qs = [l[len("You: "):] for l in history.splitlines() if l.startswith("You: ")]
    if not prev_qs:
        return question
    have = {w.strip("?.,!").lower() for w in question.split()}
    extra = []
    for w in prev_qs[-1].split():
        t = w.strip("?.,!()`'\"").lower()
        if t and t not in _STOP and t not in have and t not in extra:
            extra.append(t)
        if len(extra) >= 5:
            break
    return question + (" " + " ".join(extra) if extra else "")


def answer(
    question: str, k: int = 5, history: str | None = None,
    repos: list[str] | None = None, mem: str | None = None,
) -> tuple[str, list[dict]]:
    enhanced = _enhance_query(question, history)
    repo_ids = repos or [r["id"] for r in workspace.ready_repos()]
    # Multi-repo: ensure every selected repo is represented, not just the closest one's.
    if len(repo_ids) > 1:
        hits = retr.retrieve_covering(enhanced, repo_ids, k=k)
    else:
        hits = retr.retrieve(enhanced, k=k, repos=repos)
    if not hits:
        if mem:  # no code matched, but we remember something about the user → answer from that
            return llm.complete(SYSTEM, _build_user(question, [], history, mem)), []
        return "I couldn't find anything relevant in the ingested repos.", []
    text = llm.complete(SYSTEM, _build_user(question, hits, history, mem))
    return text, hits


def format_sources(hits: list[dict]) -> str:
    lines = ["", "Sources:"]
    for i, h in enumerate(hits, 1):
        lines.append(f"  [{i}] {h['source']} (chunk {h['chunk_index']})")
    return "\n".join(lines)
