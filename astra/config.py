"""Central config: loads .env, exposes keys + model ids, fails loudly if keys are missing."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load Astra/.env regardless of the current working directory.
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CHROMA_DIR = os.getenv("CHROMA_DIR", str(_ROOT / ".chroma"))

# Model ids — overridable via .env.
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# Embeddings: "fastembed" (local ONNX, default — no quota) or "gemini" (free tier
# has 100 contents/min + 1,000/day caps; can't bulk-ingest real repos).
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "fastembed")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384" if EMBED_PROVIDER == "fastembed" else "768"))
EMBED_GPU = os.getenv("EMBED_GPU", "1") not in ("0", "false", "no")


def require_keys() -> None:
    """Raise if required keys are missing, with a clear fix."""
    needed = [("GROQ_API_KEY", GROQ_API_KEY)]
    if EMBED_PROVIDER == "gemini":
        needed.append(("GEMINI_API_KEY", GEMINI_API_KEY))
    missing = [name for name, val in needed if not val]
    if missing:
        raise RuntimeError(
            f"Missing env vars: {', '.join(missing)}. Add them to {_ROOT / '.env'}"
        )
