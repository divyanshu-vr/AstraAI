"""Ingest a repo: walk text/code files -> chunk -> embed (Gemini) -> Chroma.

Usage: python -m astra.ingest <repo_path>
"""

import sys
from pathlib import Path

from astra import embeddings, store
from astra.chunk import split_text

TEXT_EXTS = {
    ".md", ".txt", ".rst", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".rs", ".sh", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".sql", ".html", ".css",
}
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".chroma", ".next", ".idea", ".vscode", "target", ".mypy_cache", ".pytest_cache",
}
SKIP_FILES = {"package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml", "Pipfile.lock"}
MAX_FILE_BYTES = 1_000_000


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name in SKIP_FILES or p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield p


def ingest_repo(repo_path: str, repo_id: str) -> int:
    """Chunk + embed + upsert one repo, namespaced by repo_id. Returns chunk count."""
    root = Path(repo_path).resolve()
    if not root.exists():
        raise ValueError(f"Path not found: {root}")

    files = list(iter_files(root))
    print(f"Found {len(files)} text/code files under {root}")

    ids, docs, metas = [], [], []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001 — skip unreadable files
            continue
        rel = str(f.relative_to(root))
        for i, chunk in enumerate(split_text(text)):
            ids.append(f"{repo_id}::{rel}::{i}")
            docs.append(chunk)
            metas.append({"repo": repo_id, "source": rel, "chunk_index": i, "ext": f.suffix.lower()})

    if not docs:
        raise ValueError("No chunks produced — nothing to ingest.")

    from astra import config
    print(f"Embedding {len(docs)} chunks via {config.EMBED_PROVIDER} ({config.EMBED_MODEL if config.EMBED_PROVIDER != 'gemini' else config.GEMINI_EMBED_MODEL})...")
    vectors = embeddings.embed_documents(docs)

    collection = store.get_collection()
    batch = 500  # upsert so re-ingesting the same repo is idempotent
    for i in range(0, len(docs), batch):
        collection.upsert(
            ids=ids[i : i + batch],
            documents=docs[i : i + batch],
            embeddings=vectors[i : i + batch],
            metadatas=metas[i : i + batch],
        )
    print(f"Ingested {len(docs)} chunks for '{repo_id}' (collection total: {collection.count()}).")
    return len(docs)


def ingest(repo_path: str) -> None:
    """CLI back-compat: ingest under the repo's basename as id."""
    root = Path(repo_path).resolve()
    ingest_repo(str(root), root.name.lower())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m astra.ingest <repo_path>")
    ingest(sys.argv[1])
