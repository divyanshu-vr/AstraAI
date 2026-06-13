"""Embeddings with two providers, selected via EMBED_PROVIDER:

  fastembed (DEFAULT) — local ONNX (qdrant/fastembed), BAAI/bge-small-en-v1.5 @ 384d.
      No quota, no network at query time; tries CUDA, falls back to CPU.
  gemini              — gemini-embedding-001 @ 768d. Free tier has HARD quotas
      (100 contents/min AND 1,000/day — discovered live), so it cannot bulk-ingest
      real repos; kept for paid-tier users.

Both providers L2-normalize. One provider per Chroma collection (dims differ):
reset .chroma when switching.
"""

import math
import time

from astra import config

# ---------------- fastembed (local, default) ----------------

_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        import warnings

        from fastembed import TextEmbedding

        if config.EMBED_GPU:
            try:
                import onnxruntime as ort

                if hasattr(ort, "preload_dlls"):
                    ort.preload_dlls()  # load pip-installed nvidia CUDA/cuDNN libs
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    _local_model = TextEmbedding(
                        model_name=config.EMBED_MODEL,
                        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                    )
                fell_back = any("CUDAExecutionProvider failed" in str(w.message) for w in caught)
                print(f"  fastembed: {'CPU (CUDA libs unavailable)' if fell_back else 'CUDA provider active'}")
                return _local_model
            except Exception as e:  # noqa: BLE001 — CUDA stack missing → CPU is fine
                print(f"  fastembed: CUDA init failed ({e!s:.120}) — using CPU")
        _local_model = TextEmbedding(model_name=config.EMBED_MODEL)
    return _local_model


def _fastembed_documents(texts: list[str]) -> list[list[float]]:
    model = _get_local_model()
    return [v.tolist() for v in model.passage_embed(texts)]


def _fastembed_query(text: str) -> list[float]:
    model = _get_local_model()
    return next(iter(model.query_embed(text))).tolist()


# ---------------- gemini (optional, quota-bound) ----------------

_gemini_client = None
_BATCH = 100
_RETRY_WAITS = (8, 30, 65, 70)


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        config.require_keys()
        _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini_client


def _l2_normalize(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _gemini_batch(client, batch: list[str], task_type: str):
    from google.genai import types

    for attempt, wait in enumerate(_RETRY_WAITS, 1):
        try:
            return client.models.embed_content(
                model=config.GEMINI_EMBED_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=config.EMBED_DIM
                ),
            )
        except Exception as e:  # noqa: BLE001 — back off through the quota window
            if attempt == len(_RETRY_WAITS):
                raise
            print(f"  embed retry {attempt}/{len(_RETRY_WAITS)}: {e!s:.160} (waiting {wait}s)", flush=True)
            time.sleep(wait)


def _gemini_embed(texts: list[str], task_type: str) -> list[list[float]]:
    client = _get_gemini()
    out: list[list[float]] = []
    n_batches = (len(texts) + _BATCH - 1) // _BATCH
    for b, i in enumerate(range(0, len(texts), _BATCH), 1):
        resp = _gemini_batch(client, texts[i : i + _BATCH], task_type)
        out.extend(_l2_normalize(e.values) for e in resp.embeddings)
        if i + _BATCH < len(texts) and n_batches > 1:
            print(f"  batch {b}/{n_batches} embedded — pacing for free-tier quota (61s)", flush=True)
            time.sleep(61)  # 100 contents/min; NOTE: 1,000/day cap still applies
    return out


# ---------------- public API ----------------

def embed_documents(texts: list[str]) -> list[list[float]]:
    if config.EMBED_PROVIDER == "gemini":
        return _gemini_embed(texts, "RETRIEVAL_DOCUMENT")
    return _fastembed_documents(texts)


def embed_query(text: str) -> list[float]:
    if config.EMBED_PROVIDER == "gemini":
        return _gemini_embed([text], "RETRIEVAL_QUERY")[0]
    return _fastembed_query(text)
