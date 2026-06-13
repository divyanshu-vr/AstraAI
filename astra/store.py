"""Shared Chroma collection — persistent, cosine distance (matches the normalized embeddings)."""

import chromadb

from astra import config

_COLLECTION = "astra"
_MEMORY_COLLECTION = "astra_memory"


def get_collection():
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    return client.get_or_create_collection(
        name=_COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def get_memory_collection():
    """Long-term per-user memory — kept separate from code chunks so the two never
    cross-contaminate retrieval. Same embedder/dims as the main collection."""
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    return client.get_or_create_collection(
        name=_MEMORY_COLLECTION, metadata={"hnsw:space": "cosine"}
    )
