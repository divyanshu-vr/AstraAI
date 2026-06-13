"""Retrieve top-k chunks for a question (vector search over Chroma), optionally
filtered to a set of workspace repos."""

from astra import embeddings, store


def _where(repos: list[str] | None, exts: list[str] | None):
    clauses = []
    if repos:
        clauses.append({"repo": repos[0]} if len(repos) == 1 else {"repo": {"$in": repos}})
    if exts:
        clauses.append({"ext": {"$in": exts}})
    return None if not clauses else clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _hits(res) -> list[dict]:
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    return [
        {
            "content": doc,
            "repo": meta.get("repo"),
            "source": meta.get("source"),
            "chunk_index": meta.get("chunk_index"),
            "distance": dist,
        }
        for doc, meta, dist in zip(docs, metas, dists)
    ]


def _query(qvec, where, n) -> list[dict]:
    res = store.get_collection().query(
        query_embeddings=[qvec], n_results=n, where=where,
        include=["documents", "metadatas", "distances"],
    )
    return _hits(res)


def retrieve(
    question: str,
    k: int = 5,
    repos: list[str] | None = None,
    exts: list[str] | None = None,
) -> list[dict]:
    return _query(embeddings.embed_query(question), _where(repos, exts), k)


def retrieve_covering(
    question: str, repo_ids: list[str], k: int = 5, exts: list[str] | None = None
) -> list[dict]:
    """Relevance-first top-k across the selected repos, then guarantee each selected
    repo is represented by appending its single best chunk if top-k missed it. Prevents
    one repo whose docs happen to match best from monopolizing a multi-repo answer."""
    qvec = embeddings.embed_query(question)
    hits = _query(qvec, _where(repo_ids, exts), k)
    present = {h["repo"] for h in hits}
    for rid in repo_ids:
        if rid not in present:
            extra = _query(qvec, _where([rid], exts), 1)
            if extra:
                hits.append(extra[0])
    return hits
